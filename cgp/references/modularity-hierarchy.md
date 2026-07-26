# Modularity hierarchy

A spectrum of how decoupled an implementation can be from the type it serves, from plain generic functions up to per-provider wiring, so you can pick how much CGP machinery a problem actually needs.

CGP is not all-or-nothing. The same capability — here, serializing a value with Serde — can be expressed at several levels of modularity, each more decoupled than the last and each carrying more machinery in exchange. This page walks the spectrum on one running example so a reader can stop at the first level that solves the problem rather than reaching for the heaviest tool by reflex. Assume `use cgp::prelude::*;` throughout; the CGP version is v0.8.0.

## Two questions decide the level

Before the levels, the two things that actually vary, because the level numbers name consequences while these name causes.

**What is the `Self` type?** Either a **value context** — the data the capability operates on, like the `Vec<u8>` being serialized — or an **environmental context**, a type that exists to supply choices and capabilities rather than to be operated on, like an application. Both are contexts: both sit in `Self` and both carry a wiring table. An environmental context often has no fields at all, since its whole job is to be a name the table hangs off.

**What does the capability target?** Either `Self` (**self-targeted**: `CanGreet`, `HasErrorType`, every getter) or a type parameter that `Self` only decides for (**parameter-targeted**: `CanSerializeValue<Value>`, `CanCalculateArea<Shape>`). A parameter alone does not settle this — in `CanCompute<Code, Input>` the target is `Input` while `Code` is a selector the wiring dispatches on.

Three combinations occur: a **value context** targeting `Self` (Level 3's retrofit case), an **environmental context** targeting `Self` (also Level 3, and where most CGP code lives), and an **environmental context** targeting a parameter (Levels 4–5).

**The escape from coherence happens when `Self` becomes a type you own, not when a parameter appears.** This is the part most easily misread. Wired on a foreign value type, a self-targeted component still gets one provider program-wide. Wired on an environmental context, the constraint "one wiring per type" stops binding, because you can define a second context: `App` and `TestApp` each choose their own `CanSendEmail` provider with no parameter anywhere. What Level 4's parameter adds is the ability to make that choice about types you do *not* own.

Vanilla Rust idiomatically supports only the first combination — `impl Display for String` — which is why a Rust programmer arrives with no vocabulary for the others. The other two are legal but unrewarding: an environmental context works until you factor two implementations into blanket impls and they overlap, and a parameter-targeted trait on an application type compiles fine but needs a hand-written body for every context-and-type pair. CGP's contribution is making the implementations reusable, which is what turns each arrangement into a technique.

## The coherence problem the hierarchy escapes

What forces this hierarchy to exist is Rust's coherence rules, which guarantee that every trait
lookup resolves to one globally unique implementation. Two rules enforce that uniqueness. The
**overlap rule** forbids two implementations that could both apply to the same type — you cannot
blanket-implement `Serialize` for every `T: Display` *and* for every `T: AsRef<[u8]>`, because a
`String` satisfies both and the compiler has no principled way to choose. The **orphan rule**
forbids implementing a trait for a type unless your crate owns either the trait or the type — you
cannot implement someone else's `Serialize` for someone else's `Vec<u8>`. Each level below loosens
one more of these constraints. CGP's escape route is to move the type that coherence ranges over —
the `Self` of the implementation — into a position the implementing crate always owns, then restore
a single unambiguous answer locally, one [context](components.md) at a time, through
[wiring](wiring.md). See
[coherence](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/concepts/coherence.md)
for the full framing.

## Level 1 — one implementation per interface

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

The gain is reuse with zero ceremony. The limitation is absolute: there can be exactly one blanket impl, so you cannot offer two ways to serialize bytes and let a caller pick between them.

## Level 2 — one unique implementation per type per interface

A vanilla Rust trait lifts the one-implementation limit slightly: many types may share the interface, but coherence still permits at most one implementation per type. Each type that wants the behavior writes its own impl:

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

The gain is that different types can be serialized differently. The cost is duplication: `Vec<u8>` and `&[u8]` each need an explicit impl even though the logic is identical. The body can still call out to a Level-1 building block such as `CanSerializeBytes` to share the actual work, so the duplication is confined to the boilerplate of forwarding. The remaining limitation is the one-impl-per-type ceiling — there is still no way to give `Vec<u8>` two serialization strategies and choose between them.

## Level 3 — multiple implementations per type, globally unique wiring

Applying basic CGP to a vanilla trait removes the duplication of Level 2 by turning the shared logic into a reusable [provider](components.md) and letting each type [wire](wiring.md) to it. The trait keeps its original shape, which makes the component **self-targeted** and each wired type a **value context**; `#[cgp_component]` generates the [consumer trait](components.md) and [provider trait](components.md) pair, `#[cgp_impl(new ...)]` defines a named provider once, and `delegate_components!` points each type at it. Note that Level 4 below defines a *different* component, `CanSerializeValue<Value>`, rather than revising this one:

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

The gain is real reuse without modifying the interface: `Serialize` is unchanged, so a type can still implement it directly without opting into CGP at all, and existing users of the trait are unaffected. The `SelfSerializer` provider trait removes the need for ad-hoc interfaces like `CanSerializeBytes`, and `delegate_components!` removes the manual forwarding of Level 2. The limitation is that coherence still binds the wiring itself: each type carries one global wiring, so a `Vec<u8>` entry conflicts with any overlapping `Vec<T>` entry, the choice cannot be overridden per context, and the orphan rule still means you can only wire `Vec<u8>` from a crate that owns either `Serialize` or `Vec`.

**That limitation only bites because the wired type is a value context you do not own, and this level holds a second case where it does not bite at all.** Wire a self-targeted component on an *environmental* context and the same level gives per-application choice, because you control how many contexts exist:

```rust
delegate_components! { App     { EmailSenderComponent: SendViaSmtp } }
delegate_components! { TestApp { EmailSenderComponent: RecordEmails } }
```

No parameter is involved and nothing has been worked around. That is where most CGP code lives — a capability about the application itself, wired per application — so reading Level 3 as only the retrofit case undersells it, and reading Level 4 as the first level with per-context choice is wrong.

## Level 4 — unique wiring per type, per context

Making the component **parameter-targeted** fully decouples the implementation from the type, so each context wires its own choices and the orphan rule lifts entirely. The trait changes shape: the original `Self` becomes an explicit `Value` parameter and `Self` is now always an **environmental context**, so the component dispatches on which concrete value type it serializes. What this adds over Level 3's environmental case is narrow and worth stating precisely — Level 3 already lets each context you define make its own choice, so what Level 4 buys is making that choice about types you do *not* own. Each context then folds its per-type choices straight into its own table with the `open` statement of `delegate_components!`:

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

The `open ValueSerializerComponent;` header opens the component for per-value wiring, and each `@ValueSerializerComponent.Value: Provider` entry assigns a provider for one concrete value type. The gain is that `MyAppA` and `MyAppB` resolve `Vec<u8>` to different providers — bytes versus hex — with no conflict, because each choice is coherent only within its own context. The orphan rule no longer applies: a context can wire `Vec<u8>` even when its crate owns neither `CanSerializeValue` nor `Vec`, as long as it owns the context type, so you never commit to a global serialization for `Vec` up front. The costs are that the trait must be modified to add the context parameter, and that every value type a context touches must be wired explicitly, which grows tedious for a large type set.

The `open` form rides the dispatch machinery that every `#[cgp_component]` already generates, so the trait needs no extra option. A legacy alternative writes the same dispatch with a `#[derive_delegate(UseDelegate<Value>)]` attribute on the trait and a `UseDelegate<new ValueSerializerComponents { Vec<u8>: SerializeBytes, ... }>` nested table in each context's wiring; it is retained for compatibility but `open` is preferred for new code, and the two forms appear side by side in [wiring](wiring.md).

## Level 5 — explicit wiring per type, per provider

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

Here `Vec<Vec<u8>>` serializes its inner `Vec<u8>` as hex strings, while a bare `Vec<u8>` elsewhere in the same context still serializes as bytes — the inner provider is overridden for that one branch only. Where `SerializeIteratorWith` is left without an argument, as for `Vec<u64>`, the `UseContext` default takes over and the item lookup goes back through the context, so the `u64` items resolve to `UseSerde` from the table. The gain is per-provider control: a wiring decision can be pinned at the point of use instead of globally at the context level. The cost is the higher-order plumbing itself — the extra provider parameter, the explicit context argument in the inner bound, and the discipline of choosing when to override versus when to defer to the context.

## Choosing a level

Read the spectrum as a ladder and stop at the first rung that fits. Levels 1 and 2 are plain Rust and need no CGP at all — reach for them when one implementation, or one per type, is genuinely all you need. Level 3 buys reuse and swappable providers while leaving the trait and its existing users untouched: on a value context that is the right entry point for retrofitting CGP onto an established trait, and on an environmental context it is where most CGP code lives. Level 4 pays a modified interface for the ability to choose per context about types you do not own. Level 5 is a local refinement layered on top of Level 4, used only where a single nested branch must diverge from the context's global choice. Each step up trades ceremony for decoupling, so the discipline is to climb only as far as the problem demands.

Two questions settle it faster than walking the levels. **Is the capability about the data, or about the application?** About the data means a value context and Level 3's retrofit case; about the application means an environmental context. **Does it concern a type you do not own, which different applications must treat differently?** If yes, the target moves into a parameter and you are at Level 4; if no, self-targeting is enough. Each arrangement answers a different question rather than representing a different amount of sophistication.

Further reference:
[coherence](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/concepts/coherence.md)
for the rules this hierarchy escapes, and
[modular serialization](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/examples/modular-serialization.md)
for the full worked example.
