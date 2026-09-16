# Modularity hierarchy

Choose the least complex form that gives callers the implementation choices they need. CGP supports
a progression from plain generic functions to wiring choices inside individual providers. This
reference compares those forms using serialization as a running example.

Each tier separates the implementation from the type it serves more fully, at the cost of additional
declarations or wiring. Stop at the tier that solves the problem. The examples assume
`use cgp::prelude::*;` and describe CGP v0.8.0.

## The questions that decide the tier

Identify the context and the operation's target before choosing a tier. These roles determine where
provider choices belong and whether different applications can make independent choices.

The context occupies the `Self` position. A **value context** is the data being operated on, such as
the `Vec<u8>` being serialized. An **environmental context** supplies an application's choices and
capabilities. Both can carry wiring, but an environmental context may be fieldless because it exists
only to select providers.

The target is either `Self` or a type parameter. Self-targeted components include `CanGreet` and
`HasErrorType`; parameter-targeted components include `CanSerializeValue<Value>` and
`CanCalculateArea<Shape>`. Not every parameter is a target: in `CanCompute<Code, Input>`, `Input` is
the target and `Code` selects the wiring.

Tier 3 covers both value contexts targeting themselves and environmental contexts supplying their
own capabilities. Tiers 4 and 5 use environmental contexts to choose behavior for a separate target
type.

Owning the context permits independent wiring choices even without a target parameter. A foreign
value type has one wiring program-wide, but a crate can define `App` and `TestApp` and choose a
different `CanSendEmail` provider for each. Tier 4 adds the ability to make those per-context
choices about separate types, including types the crate does not own.

Ordinary Rust supports these arrangements, but reusable implementations can encounter coherence
restrictions. Environmental contexts with overlapping blanket impls still conflict, and a
parameter-targeted trait may require manual forwarding for each context-and-type pair. CGP separates
reusable providers from the contexts that select them.

## The coherence problem the hierarchy escapes

Rust's coherence rules require trait implementations to be unambiguous. The overlap rule rejects
impls that could apply to the same type. For example, blanket impls for every `T: Display` and every
`T: AsRef<[u8]>` conflict because `String` satisfies both. The orphan rule also restricts impls
involving foreign traits and types; a crate cannot implement someone else's `Serialize` for someone
else's `Vec<u8>`.

CGP gives each implementation an owned provider type and lets a [context](components.md) select it
through [wiring](wiring.md). Coherence still applies, but implementations can coexist because they
belong to different providers. Each context then supplies an unambiguous choice. See
[coherence](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/concepts/coherence.md)
for the full rules.

## Tier 1: one implementation per interface

Use a generic function or blanket trait impl when one shared implementation is enough. A generic
function keeps its logic and requirements together:

```rust
pub fn serialize_bytes<Value: AsRef<[u8]>, S: Serializer>(
    value: &Value,
    serializer: S,
) -> Result<S::Ok, S::Error> { ... }
```

A blanket trait exposes the shared implementation as a method and keeps its dependencies on the
impl. Callers can require the trait instead of repeating those dependencies:

```rust
pub trait CanSerializeBytes {
    fn serialize_bytes<S: Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error>;
}

impl<Value: AsRef<[u8]>> CanSerializeBytes for Value {
    fn serialize_bytes<S: Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> { ... }
}
```

This form reuses the implementation without wiring. It does not let a context choose another
implementation for types already covered by the blanket impl.

## Tier 2: one unique implementation per type per interface

Use ordinary per-type trait impls when types need different behavior but each type needs only one
implementation. Coherence permits one impl per type for this interface:

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

Per-type impls let types serialize differently, but each type must supply an impl. `Vec<u8>` and
`&[u8]` can share the work through the tier-1 `CanSerializeBytes` trait, as above, while repeating
the forwarding method. A single type still cannot choose between two implementations of the same
trait.

## Tier 3: multiple implementations per type, globally unique wiring

Use providers to share implementations while preserving an existing trait's interface. In this
example, `Serialize` remains self-targeted and each wired value type is its context.
`#[cgp_component]` generates the consumer/provider trait pair, `#[cgp_impl]` defines the reusable
provider, and `delegate_components!` selects it for each type:

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

Providers remove the manual forwarding while preserving the consumer interface. Existing callers
still use `Serialize`, and types can still implement that trait directly. The `SelfSerializer`
provider trait supplies the reusable interface that the separate `CanSerializeBytes` trait supplied
in tier 2.

Wiring on a value type remains globally unique. A `Vec<u8>` entry conflicts with an overlapping
`Vec<T>` entry, and another application cannot override it for the same value type. Wiring a foreign
value type also requires ownership of the relevant component key, supplied by the crate defining the
component.

An owned environmental context allows per-application choices at this same tier. Define separate
context types and wire the self-targeted component independently on each:

```rust
delegate_components! { App     { EmailSenderComponent: SendViaSmtp } }
delegate_components! { TestApp { EmailSenderComponent: RecordEmails } }
```

`App` sends email through SMTP, while `TestApp` records it. This common CGP arrangement does not
need a target parameter: each context chooses a capability about itself. Tier 4 extends that choice
to a separate target type.

## Tier 4: unique wiring per type, per context

Use a parameter-targeted component when each context must choose behavior for a separate value type.
The serialized value moves from `Self` to a `Value` parameter, and `Self` becomes the environmental
context. This defines a different component, `CanSerializeValue<Value>`, from tier 3's `Serialize`.

Each context uses `open` to select a provider per value type. Here, the applications agree on
`Vec<u64>` but choose different representations for `Vec<u8>`:

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

`MyAppA` serializes `Vec<u8>` as bytes, while `MyAppB` serializes it as hex. Each
`@ValueSerializerComponent.Value: Provider` entry records a choice on its own context, so the
choices do not conflict.

Owning the context satisfies the ownership requirement even when the component and value type are
foreign. Rust's orphan rule still applies; the owned context makes this wiring legal. The tradeoff
is a changed interface and explicit wiring for the value types the application uses.

`open` uses the dispatch support generated by every `#[cgp_component]`. Older code adds
`#[derive_delegate(UseDelegate<Value>)]` to the trait and stores dispatch entries in
`UseDelegate<new ValueSerializerComponents { … }>`. That form remains for compatibility; prefer
`open` for new wiring. See [wiring](wiring.md) for both forms.

## Tier 5: explicit wiring per type, per provider

Use a [higher-order provider](higher-order-providers.md) when one nested operation must differ from
the context's usual choice. Its inner provider can default to `UseContext`, which resolves through
the context, while an explicit argument selects a provider for that operation alone:

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

`Vec<Vec<u8>>` serializes its inner vectors as hex, while a standalone `Vec<u8>` still serializes as
bytes. The explicit `SerializeHex` argument changes only that nested operation.

The default inner provider preserves the context's choices elsewhere. For `Vec<u64>`,
`SerializeIteratorWith` uses `UseContext`, so each `u64` resolves to `UseSerde` through the table.
This local control requires an extra provider parameter and a bound describing the inner operation.
The higher-ranked bound remains explicit in this example.

## Choosing a tier

Choose a tier by the scope of the implementation choice:

| Need | Form |
| --- | --- |
| One shared implementation | Tier 1: generic function or blanket trait |
| One implementation per type | Tier 2: ordinary trait impls |
| Reusable providers for a self-targeted capability | Tier 3: component wiring |
| A provider choice per context and target type | Tier 4: parameter-targeted component |
| A different choice for one nested operation | Tier 5: higher-order provider |

Tiers 1 and 2 use plain Rust. Tier 3 preserves the consumer interface and supports both retrofitting
a value trait and selecting application capabilities. Tier 4 changes the interface to separate the
context from the target. Tier 5 adds local control over nested calls.

Start by deciding whether `Self` represents the data or the application. If it represents the
application, use a target parameter when the operation concerns a separate type whose behavior must
vary by application. Add an explicit inner provider only when a nested call must differ from that
context's normal choice.

Read these references for the rules and the complete example:

- [Coherence](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/concepts/coherence.md): Ownership and overlap restrictions.
- [Modular serialization](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/examples/modular-serialization.md): The full serialization example.
