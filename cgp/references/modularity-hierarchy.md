
# Modularity Hierarchy

This section summarizes the modularity hierarchy of the use of CGP and vanilla Rust constructs, using the `Serialize` trait from `serde` as the base example.

## One Implementation per Interface

- Generic functions and blanket implementations allow the definition of exactly one implementation of the interface they define.
- Example generic function:

```rust
pub fn serialize_bytes<Value: AsRef<[u8]>, S: Serializer>(value: &Value, serializer: S) -> Result<S::Ok, S::Error> { ... }
```

- Blanket traits have the same limitations, but improve the ergonomic of generic functions by hiding the constraints behind the trait impl:

```rust
pub trait CanSerializeBytes {
    fn serialize_bytes<S: Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error>;
}

impl<Value: AsRef<[u8]>> CanSerializeBytes for Value {
    fn serialize_bytes<S: Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> { ... }
}
```

## One Unique Implementation per Type per Interface

- Vanilla Rust traits allows multiple implementations to share the same interface, but the coherence restrictions allows at most one unique implementation per type for the interface they define.
- Example:

```rust
pub trait Serialize {
    fn serialize<S: Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error>
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

- The above example requires two explicit implementations of `Serialize` for `Vec<u8>` and `&[u8]`, even though both implementations share the same logic.
  - However, the method implementation body can make use of explicit implementations earlier such as `CanSerializeBytes` to create reusable building blocks outside of the trait system.

## Multiple Implementations per Type per Interface, Globally Unique Wiring per Type

- Basic CGP techniques can be applied on vanilla Rust traits to streamline the reuse of common implementation logic through provider traits.
- Example:

```rust
#[cgp_component(ValueSerializer)]
pub trait Serialize {
    fn serialize<S: Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error>
}

#[cgp_impl(new SerializeBytes)]
impl<Value: AsRef<[u8]>> ValueSerializer for Value {
    fn serialize_bytes<S: Serializer>(&self, serializer: S) -> Result<S::Ok, S::Error> { ... }
}

delegate_components! {
    Vec<u8> {
        ValueSerializerComponent: SerializeBytes,
    }
}

delegate_components! {
    <'a> &'a [u8] {
        ValueSerializerComponent: SerializeBytes,
    }
}
```

- The main advantage of this base approach is that the original `Serialize` trait is extended without modification to the original interface. This provides backward compatibility with existing Rust traits that are already widely used.
    - A type can still implements `Serialize` directly without needing to opt in to use CGP for everything.
- The use of the `ValueSerializer` provider trait removes the need to write explicit interfaces like `CanSerializeBytes`.
- The use of `delegate_components!` removes the need to manually forward the method implementation through explicit method calls.
- The main limitation is that some coherence restrictions still apply.
    - If we have an explicit `delegate_components!` wiring of `Vec<u8>` to `SerializeBytes`, then we cannot have a separate overlapping implementation or wiring for a generic `Vec<T>`.
    - The `Serialize` implementation for a type like `Vec<u8>` cannot be easily overridden for a specific context, such as to serialize a custom `Vec<u8>` field in a struct as hex string instead of bytes.
    - The orphan rules still apply, so the use of `delegate_components!` cannot be applied to `Vec<u8>` outside of a crate that owns either `Serialize` or `Vec`.

## Multiple Implementations per Type per Interface, Unique Wiring per Type per Context

- CGP supports full decoupling of an implementation from the type being implemented, by adding an explicit context parameter to configure the wiring of multiple types within the context.
- For example, the `Serialize` trait is changed to `CanSerializeValue`, with the original `Self` type moved to become an explicit `Value` parameter:

```rust
#[cgp_component {
    provider: ValueSerializer,
    derive_delegate: UseDelegate<Value>,
}]
pub trait CanSerializeValue<Value: ?Sized> {
    fn serialize<S>(&self, value: &Value, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer;
}

delegate_components! {
    new MyAppA {
        ValueSerializerComponent:
            UseDelegate<new ValueSerializerComponents {
                Vec<u8>: SerializeBytes,
                Vec<u64>: SerializeIterator,
                ...
            }>,
    }
}

delegate_components! {
    new MyAppB {
        ValueSerializerComponent:
            UseDelegate<new ValueSerializerComponents {
                Vec<u8>: SerializeHex,
                Vec<u64>: SerializeIterator,
                ...
            }>,
    }
}
```

- This allows explicit context types like `MyAppA` and `MyAppB` to be defined with different providers chosen for a type like `Vec<u8>`.
- The orphan rules no longer apply, so a context like `MyAppA` can wire the implementation of `Vec<u8>`, even if the crate don't own `CanSerializeValue` or `Vec`, as long as the crate owns the context `AppA`.
- The coherence restrictions are almost fully lifted, since the orphan wiring of a type like `Vec` means that we don't need to commit to a global implementation for `Vec` up front.
- The main disadvantage is that the trait needs to be modified to add an explicit context parameter for wiring.
- Furthermore, explicit wiring must be specified for all types used within a context, which can be tedious.

## Multiple Implementations per Type per Interface, Explicit Wiring Per Type per Provider

- The use of higher order providers together with `UseContext` allows the wiring of the implementation of a type to be overridden within a provider, without routing it through the context.
- For example:

```rust
pub struct SerializeIteratorWith<Provider = UseContext>(pub PhantomData<Provider>);

#[cgp_impl(SerializeIteratorWith<Provider>)]
impl<Context, Value, Provider> ValueSerializer<Value> for Context
where
    for<'a> &'a Value: IntoIterator,
    Provider: for<'a> ValueSerializer<Context, <&'a Value as IntoIterator>::Item>,
{
    fn serialize<S>(&self, value: &Value, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    { ... }
}

delegate_components! {
    new MyAppA {
        ValueSerializerComponent:
            UseDelegate<new ValueSerializerComponents {
                Vec<u8>: SerializeBytes,
                Vec<Vec<u8>>: SerializeIteratorWith<SerializeHex>,
                Vec<u64>: SerializeIteratorWith,
                [
                    u8,
                    u64,
                ]:
                    UseSerde,
                ...
            }>,
    }
}
```

- In the above example, the serialization of `Vec<Vec<u8>>` would serialize the inner `Vec<u8>` as hex strings, while other `Vec<u8>` would still be serialized as bytes.
- The default parameter allows the inner item serializer to be routed through the context as usual, if no overridding is required.
    - The example `Vec<u64>` serialization would still go through the context, which result in `UseSerde` being used to serialize the `u64` items.
- This patterns allows further fine grained control of the wiring implementations that can be overridden locally on a per-provider basis, as compared a more "global" wiring at the per-context level.
