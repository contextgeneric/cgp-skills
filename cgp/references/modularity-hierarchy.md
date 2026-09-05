# Modularity hierarchy

This file lays out a hierarchy of how decoupled an implementation can be from the type it serves, from plain generic functions up to per-provider wiring, so you can pick how much CGP machinery a problem needs.

CGP is not all-or-nothing. The same capability, here serializing a value with Serde, can be expressed at several tiers of modularity. Each tier is more decoupled than the last and carries more machinery in exchange. This page walks the hierarchy on one running example, so a reader can stop at the first tier that solves the problem rather than reaching for the heaviest tool by reflex. Assume `use cgp::prelude::*;` throughout. The CGP version is v0.8.0.

## The questions that decide the tier

Before the tiers, consider what varies, because the tier numbers name consequences while these questions name causes.

**What is the `Self` type?** It is either a **value context**, the data the capability operates on, like the `Vec<u8>` being serialized, or an **environmental context**, a type that exists to supply choices and capabilities rather than to be operated on, like an application. Both are contexts. Both sit in `Self` and both carry a wiring table. An environmental context often lacks fields entirely, since its whole job is to be a name the table hangs off.

**What does the capability target?** It targets either `Self` (**self-targeted**: `CanGreet`, `HasErrorType`, every getter) or a type parameter that `Self` only decides for (**parameter-targeted**: `CanSerializeValue<Value>`, `CanCalculateArea<Shape>`). A parameter alone does not settle this. In `CanCompute<Code, Input>` the target is `Input`, while `Code` is a selector the wiring dispatches on.

The combinations that occur are a **value context** targeting `Self` (tier 3's retrofit case), an **environmental context** targeting `Self` (also tier 3, and where most CGP code lives), and an **environmental context** targeting a parameter (tiers 4 and 5).

**The escape from coherence happens when `Self` becomes a type you own, not when a parameter appears.** This is the part most easily misread. Wired on a foreign value type, a self-targeted component still gets one provider program-wide. Wired on an environmental context, the constraint "one wiring per type" stops binding, because you can define a second context. `App` and `TestApp` each choose their own `CanSendEmail` provider without a parameter anywhere. Tier 4's parameter adds the ability to make that choice about types you do *not* own.

Vanilla Rust idiomatically supports only the value-context arrangement, as in `impl Display for String`, so a Rust programmer arrives without vocabulary for the others. The other arrangements are legal but unrewarding. An environmental context works until you factor two implementations into blanket impls and they overlap, and a parameter-targeted trait on an application type compiles fine but needs a hand-written body for every context-and-type pair. CGP's contribution is making the implementations reusable, and that turns each arrangement into a technique.

## The coherence problem the hierarchy escapes

This hierarchy exists because of Rust's coherence rules, which guarantee that every trait lookup resolves to one globally unique implementation. Rust enforces that uniqueness with the overlap rule and the orphan rule. The **overlap rule** forbids two implementations that could both apply to the same type. You cannot blanket-implement `Serialize` for every `T: Display` *and* for every `T: AsRef<[u8]>`, because a `String` satisfies both and the compiler cannot choose in a principled way. The **orphan rule** forbids implementing a trait for a type unless your crate owns either the trait or the type. You cannot implement someone else's `Serialize` for someone else's `Vec<u8>`. Each tier below loosens one more of these constraints. CGP's escape route is to move the type that coherence ranges over, the `Self` of the implementation, into a position the implementing crate always owns, then restore a single unambiguous answer locally, one [context](components.md) at a time, through [wiring](wiring.md). See [coherence](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/concepts/coherence.md) for the full framing.

## Tier 1: one implementation per interface

The least machinery is a generic function or a blanket trait impl, which both define exactly one implementation behind an interface. A generic function captures the logic and its bounds in one place:

```rust
pub fn serialize_bytes<Value: AsRef<[u8]>, S: Serializer>(
    value: &Value,
    serializer: S,
) -> Result<S::Ok, S::Error> { ... }
```

A blanket trait carries the same one-implementation limitation but reads more ergonomically at the call site, since the bound hides behind the trait impl and the caller writes a method:

```rust
pub trait CanSerializeBytes {
    fn serialize_bytes<S: Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error>;
}

impl<Value: AsRef<[u8]>> CanSerializeBytes for Value {
    fn serialize_bytes<S: Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> { ... }
}
```

The gain is reuse with zero ceremony. The limitation is absolute. There can be exactly one blanket impl, so you cannot offer two ways to serialize bytes and let a caller pick between them.

## Tier 2: one unique implementation per type per interface

A vanilla Rust trait lifts the one-implementation limit slightly. Many types may share the interface, but coherence still permits at most one implementation per type. Each type that wants the behavior writes its own impl:

```rust
pub trait Serialize {
    fn serialize<S: Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error>;
}

impl Serialize for Vec<u8> {
    fn serialize<S: Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        self.serialize_bytes(serializer)
    }
}

impl<'a> Serialize for &'a [u8] {
    fn serialize<S: Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> {
        self.serialize_bytes(serializer)
    }
}
```

The gain is that different types can be serialized differently. The cost is duplication. `Vec<u8>` and `&[u8]` each need an explicit impl even though the logic is identical. The body can still call out to a tier-1 building block such as `CanSerializeBytes` to share the actual work, so the duplication is confined to the boilerplate of forwarding. The remaining limitation is the one-impl-per-type ceiling. `Vec<u8>` still cannot have two serialization strategies to choose between.

## Tier 3: multiple implementations per type, globally unique wiring

Applying basic CGP to a vanilla trait removes the duplication of tier 2 by turning the shared logic into a reusable [provider](components.md) and letting each type [wire](wiring.md) to it. The trait keeps its original shape, which makes the component **self-targeted** and each wired type a **value context**. `#[cgp_component]` generates the [consumer trait](components.md) and [provider trait](components.md) pair, `#[cgp_impl(new ...)]` defines a named provider once, and `delegate_components!` points each type at it. Note that tier 4 below defines a *different* component, `CanSerializeValue<Value>`, rather than revising this one:

```rust
#[cgp_component(SelfSerializer)]
pub trait Serialize {
    fn serialize<S: Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error>;
}

#[cgp_impl(new SerializeSelfAsBytes)]
#[uses(AsRef<[u8]>)]
impl SelfSerializer {
    fn serialize<S: Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> { ... }
}

delegate_components! {
    Vec<u8> {
        SelfSerializerComponent: SerializeSelfAsBytes,
    }
}

delegate_components! {
    <'a> &'a [u8] {
        SelfSerializerComponent: SerializeSelfAsBytes,
    }
}
```

The gain is real reuse without modifying the interface. `Serialize` is unchanged, so a type can still implement it directly without opting into CGP at all, and existing users of the trait are unaffected. The `SelfSerializer` provider trait removes the need for ad-hoc interfaces like `CanSerializeBytes`, and `delegate_components!` removes the manual forwarding of tier 2. The limitation is that coherence still binds the wiring itself. Each type carries one global wiring, so a `Vec<u8>` entry conflicts with any overlapping `Vec<T>` entry, the choice cannot be overridden per context, and the orphan rule still means you can only wire `Vec<u8>` from a crate that owns either `Serialize` or `Vec`.

**That limitation only bites because the wired type is a value context you do not own, and this tier holds another case where it does not bite at all.** Wire a self-targeted component on an *environmental* context and the same tier gives per-application choice, because you control how many contexts exist:

```rust
delegate_components! { App     { EmailSenderComponent: SendViaSmtp } }
delegate_components! { TestApp { EmailSenderComponent: RecordEmails } }
```

This involves neither a parameter nor a workaround. That is where most CGP code lives, a capability about the application itself, wired per application. So reading tier 3 as only the retrofit case undersells it, and reading tier 4 as the first tier with per-context choice is wrong.

## Tier 4: unique wiring per type, per context

Making the component **parameter-targeted** fully decouples the implementation from the type, so each context wires its own choices and the orphan rule lifts entirely. The trait changes shape. The original `Self` becomes an explicit `Value` parameter and `Self` is now always an **environmental context**, so the component dispatches on which concrete value type it serializes. The addition over tier 3's environmental case is narrow. Tier 3 already lets each context you define make its own choice, so tier 4 buys only the ability to make that choice about types you do *not* own. Each context then folds its per-type choices straight into its own table with the `open` statement of `delegate_components!`:

```rust
#[cgp_component(ValueSerializer)]
pub trait CanSerializeValue<Value: ?Sized> {
    fn serialize<S>(&self, value: &Value, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer;
}

delegate_components! {
    new MyAppA {
        open ValueSerializerComponent;

        @ValueSerializerComponent.Vec<u8>: SerializeBytes,
        @ValueSerializerComponent.Vec<u64>: SerializeIterator,
    }
}

delegate_components! {
    new MyAppB {
        open ValueSerializerComponent;

        @ValueSerializerComponent.Vec<u8>: SerializeHex,
        @ValueSerializerComponent.Vec<u64>: SerializeIterator,
    }
}
```

The `open ValueSerializerComponent;` header opens the component for per-value wiring, and each `@ValueSerializerComponent.Value: Provider` entry assigns a provider for one concrete value type. The gain is that `MyAppA` and `MyAppB` resolve `Vec<u8>` to different providers, bytes versus hex, without conflict, because each choice is coherent only within its own context. The orphan rule no longer applies. A context can wire `Vec<u8>` even when its crate owns neither `CanSerializeValue` nor `Vec`, as long as it owns the context type, so you never commit to a global serialization for `Vec` up front. The costs are that the trait must be modified to add the context parameter, and that every value type a context touches must be wired explicitly, which grows tedious for a large type set.

The `open` form rides the dispatch machinery that every `#[cgp_component]` already generates, so the trait does not need an extra option. A legacy alternative writes the same dispatch with a `#[derive_delegate(UseDelegate<Value>)]` attribute on the trait and a `UseDelegate<new ValueSerializerComponents { Vec<u8>: SerializeBytes, ... }>` nested table in each context's wiring. It is retained for compatibility, but `open` is preferred for new code, and both forms appear side by side in [wiring](wiring.md).

## Tier 5: explicit wiring per type, per provider

The finest grain overrides wiring *inside* a provider rather than at the context, using a [higher-order provider](higher-order-providers.md) whose inner provider defaults to `UseContext`. The default routes nested lookups back through the context as usual, while an explicit inner provider overrides one branch locally without touching the context's table:

```rust
pub struct SerializeIteratorWith<Provider = UseContext>(pub PhantomData<Provider>);

#[cgp_impl(SerializeIteratorWith<Provider>)]
impl<Value, Provider> ValueSerializer<Value>
where
    for<'a> &'a Value: IntoIterator,
    Provider: for<'a> ValueSerializer<Self, <&'a Value as IntoIterator>::Item>,
{
    fn serialize<S>(&self, value: &Value, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    { ... }
}

delegate_components! {
    new MyAppA {
        open ValueSerializerComponent;

        @ValueSerializerComponent.Vec<u8>: SerializeBytes,
        @ValueSerializerComponent.Vec<Vec<u8>>: SerializeIteratorWith<SerializeHex>,
        @ValueSerializerComponent.Vec<u64>: SerializeIteratorWith,
        @ValueSerializerComponent.[u8, u64]: UseSerde,
    }
}
```

Here `Vec<Vec<u8>>` serializes its inner `Vec<u8>` as hex strings, while a bare `Vec<u8>` elsewhere in the same context still serializes as bytes. The inner provider is overridden for that one branch only. Where `SerializeIteratorWith` is left without an argument, as for `Vec<u64>`, the `UseContext` default takes over and the item lookup goes back through the context, so the `u64` items resolve to `UseSerde` from the table. The gain is per-provider control. A wiring decision can be pinned at the point of use instead of globally at the context level. The cost is the higher-order plumbing itself: the extra provider parameter, the explicit context argument in the inner bound, and the discipline of choosing when to override versus when to defer to the context.

## Choosing a tier

Settle at the first tier that fits. Tiers 1 and 2 are plain Rust and do not need CGP at all. Reach for them when one implementation, or one per type, is all you need. Tier 3 buys reuse and swappable providers while leaving the trait and its existing users untouched. On a value context it is the right entry point for retrofitting CGP onto an established trait, and on an environmental context it is where most CGP code lives. Tier 4 pays a modified interface for the ability to choose per context about types you do not own. Tier 5 is a local refinement layered on top of tier 4, used only where a single nested branch must diverge from the context's global choice. Each higher tier trades ceremony for decoupling, so the discipline is to go only as far as the problem demands.

Asking the right questions settles it faster than working through the tiers one by one. **Is the capability about the data, or about the application?** About the data means a value context and tier 3's retrofit case. About the application means an environmental context. **Does it concern a type you do not own, which different applications must treat differently?** If yes, the target moves into a parameter and you are at tier 4. If no, self-targeting is enough. Each arrangement answers a different question rather than representing a different amount of sophistication.

Further reference:
[coherence](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/concepts/coherence.md)
for the rules this hierarchy escapes, and
[modular serialization](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/examples/modular-serialization.md)
for the full worked example.
