# Components

A CGP component separates the trait callers use from the trait providers implement.
`#[cgp_component]` generates the traits and delegation support from one trait definition. Read this
reference before working with components or providers.

## What a component is

A component contains a consumer trait, a provider trait, a `…Component` marker, and blanket impls
that connect them. The consumer trait is the interface callers use, while the provider trait accepts
implementations on separate provider types. This separation allows interchangeable implementations
and capabilities for types the implementing crate does not own.

Ordinary trait implementations tie an interface to its implementation on a type. The type receiving
`.area()` also supplies the trait impl, and coherence permits only one impl of that trait for that
type. CGP moves the implementation choice to the provider.

The examples use CGP v0.8.0 and assume `use cgp::prelude::*;`. They follow a greeting component
(`CanGreet`, `Greeter`, and `GreetHello`) on `Person`, and an area component (`CanCalculateArea`,
`AreaCalculator`, and `RectangleArea`) on `Rectangle`.

## What `#[cgp_component(Greeter)]` generates

Applying the macro to a consumer trait produces the consumer trait, the provider trait, the blanket
impls that connect them, and the marker struct. Start from the trait, naming the provider trait in
the attribute argument:

```rust
#[cgp_component(Greeter)]
pub trait CanGreet {
    fn greet(&self);
}
```

The **consumer trait** is emitted unchanged. This is the self-style trait callers use (`CanDoX`), so
a caller writes `person.greet()` exactly as with any trait:

```rust
pub trait CanGreet {
    fn greet(&self);
}
```

The **provider trait** is the same interface with `Self` moved out into an explicit leading
`Context` type parameter and every `self`/`Self` rewritten to `context`/`Context`. It is named in
noun form (`SomethingDoer`, or `…Provider` when a noun does not fit). It carries an `IsProviderFor`
supertrait that captures the component, the context, and a `Params` tuple of any extra type
parameters, which is `()` when there are none:

```rust
pub trait Greeter<Context>:
    IsProviderFor<GreeterComponent, Context, ()>
{
    fn greet(context: &Context);
}
```

Implement a provider trait on a dedicated zero-sized provider struct. The struct serves only as a
type-level marker and is never instantiated. Each provider owns a distinct `Self` type while
remaining generic over `Context`, allowing `GreetHello`, `GreetGoodbye`, and other implementations
to coexist. See [bypassing
coherence](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/concepts/coherence.md)
for the coherence rules and [modularity hierarchy](modularity-hierarchy.md) for when to use this
separation.

## How the two traits connect

Generated blanket impls connect consumer calls to the chosen provider. Together they resolve
`person.greet()` without requiring the caller to name a provider. The macros generate these impls;
you do not write them.

The **consumer blanket impl** says that any context implementing the provider trait *for itself*
gets the consumer trait. It forwards `context.greet()` to `Context::greet(self)`:

```rust
impl<Context> CanGreet for Context
where
    Context: Greeter<Context>,
{
    fn greet(&self) {
        Context::greet(self)
    }
}
```

The **provider blanket impl** lets any provider that delegates this component inherit the provider
trait from whatever it delegates to. The delegation is a type-level table lookup through
`DelegateComponent`, keyed on the `GreeterComponent` marker:

```rust
impl<Context, Provider> Greeter<Context> for Provider
where
    Provider: DelegateComponent<GreeterComponent>
        + IsProviderFor<GreeterComponent, Context, ()>,
    Provider::Delegate: Greeter<Context>,
{
    fn greet(context: &Context) {
        Provider::Delegate::greet(context)
    }
}
```

The **component marker** is a zero-sized key into those delegation tables:

```rust
pub struct GreeterComponent;
```

These examples use readable names for clarity. The emitted code uses reserved identifiers,
`__Context__` for the context parameter (overridable) and `__Provider__` for the provider parameter,
chosen so they never clash with a user's own type names.

## Wiring is the table lookup that ties it all together

Wiring selects the provider that the generated impls use for each component. In this example,
`Person` delegates `GreeterComponent` to `GreetHello`. A call to `person.greet()` enters the
consumer blanket impl, which requires `Person: Greeter<Person>`. The provider blanket impl satisfies
that requirement through the delegation entry and forwards the call to `GreetHello`. Changing the
entry changes the selected behavior:

```rust
#[derive(HasField)]
pub struct Person {
    pub name: String,
}

delegate_components! {
    Person {
        GreeterComponent: GreetHello,
    }
}
```

The full table grammar, including per-value dispatch and presets, lives in [wiring](wiring.md). This
file shows only the single-entry form needed to make the resolution concrete.

## Why `IsProviderFor` exists

`IsProviderFor` exposes missing provider dependencies in compiler errors. It is an empty marker used
as a supertrait on every provider trait. Checking a provider trait directly can yield only “trait
not implemented” because the competing provider blanket impl suppresses Rust's detailed explanation.

The macros implement `IsProviderFor` with the same `where` bounds as the provider-trait impl.
Without a competing blanket candidate for this check, Rust reports the specific unsatisfied bound.
An `IsProviderFor` error therefore identifies a dependency preventing the provider-trait impl from
applying. The macros generate and use the marker; you encounter it in diagnostics:

```rust
#[diagnostic::on_unimplemented(
    note = "You need to add `#[cgp_provider({Component})]` on the impl block for CGP provider traits"
)]
pub trait IsProviderFor<Component, Context, Params: ?Sized = ()> {}
```

## Writing providers

Prefer `#[cgp_impl]` when writing providers. It accepts consumer-style signatures and expands to the
explicit provider forms described below. Use those lower-level forms directly only when you need the
native provider-trait structure.

`#[cgp_provider]` preserves an explicit provider-trait impl and generates an `IsProviderFor` impl
with the same `where` bounds. The provider struct must already exist, as it does here:

```rust
pub struct RectangleArea;

#[cgp_provider]
impl<Context> AreaCalculator<Context> for RectangleArea
where
    Context: HasDimensions,
{
    fn area(context: &Context) -> f64 {
        context.width() * context.height()
    }
}
```

The generated marker impl repeats the `HasDimensions` bound, allowing a missing dependency to appear
by name in an error:

```rust
impl<Context> IsProviderFor<AreaCalculatorComponent, Context, ()> for RectangleArea
where
    Context: HasDimensions,
{}
```

The optional attribute argument overrides the component type, which otherwise defaults to the
provider trait's name plus a `Component` suffix. Pass it explicitly only when the trait name does
not follow that convention.

`#[cgp_new_provider]` also declares the provider struct. It otherwise behaves like
`#[cgp_provider]`, letting an explicit provider impl introduce its struct in the same block. A
generic provider receives a `PhantomData` field over its parameters.

`#[cgp_impl]` lets providers use `self`, `Self`, and consumer-style method signatures. The attribute
names the provider, and `new` declares its struct. Omitting `for Context` lets the macro insert the
context parameter:

```rust
#[cgp_impl(new RectangleArea)]
impl AreaCalculator
where
    Self: HasDimensions,
{
    fn area(&self) -> f64 {
        self.width() * self.height()
    }
}
```

Inside `#[cgp_impl]`, `self` and `Self` refer to the context. The macro rewrites them to the context
value and type. The provider struct remains a type-level name without a runtime instance.

`#[cgp_impl]` desugars to `#[cgp_provider]`, or to `#[cgp_new_provider]` when `new` is given. The
block above is equivalent to writing the context out by hand and lowering it:

```rust
#[cgp_new_provider]
impl<__Context__> AreaCalculator<__Context__> for RectangleArea
where
    __Context__: HasDimensions,
{
    fn area(__context__: &__Context__) -> f64 {
        __context__.width() * __context__.height()
    }
}
```

The receiver `&self` became `__context__: &__Context__`, where the receiver identifier is the
snake-cased context name wrapped in double underscores, and `Self` in the `where` clause became the
context type. When you write `for Context` explicitly, that name is used instead of `__Context__`.
Do so when you need to bound or refer to the context readably.

## Impl-side dependencies

Impl-side dependencies are provider requirements that the consumer trait does not expose.
`RectangleArea` requires `Context: HasDimensions`, while `CanCalculateArea` declares only `area`. A
caller bounded by `CanCalculateArea` need not repeat `HasDimensions`, so the dependency does not
propagate through callers.

The provider states these requirements in its `where` clause, and wiring resolves them through the
context. This supplies dependency injection while preserving a smaller consumer interface. See
[impl-side
dependencies](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/concepts/impl-side-dependencies.md)
for the full explanation and [functions and getters](functions-and-getters.md) for implicit
arguments and getters that read context fields.

## Which items belong in one component

Group component items according to the provider choice that determines their implementation. A
component trait can contain as many items as an ordinary Rust trait, but one provider supplies them
all. Keep items together when one choice determines them; separate items that need independent
choices. Single-method components are common because many application capabilities represent one
choice.

A method and its associated output type often belong in one component. The provider chooses both the
operation and its result type. `CanCompute`, `CanHandle`, and `CanProduce` therefore define `Output`
alongside their methods. Likewise, a `CanQueryDatabase` component can group `Row` with `query`,
preventing a context from independently pairing a Postgres query provider with a SQLite row type.

A getter component can group fields read by their method names. One `UseFields` provider supplies
all those reads. However, `UseField` and `WithProvider` impls are generated only for single-method
getters, so accessing a differently named field requires a separate component.

Grouping independent choices increases the dependencies and forwarding code each provider must
support. Every provider must satisfy the union of its methods' dependencies, imposing those
requirements on each context that uses it. A [higher-order provider](higher-order-providers.md) must
implement every item, including forwarding methods it leaves unchanged.

Contexts using only part of a component must still supply the complete interface. This often leads
to placeholder associated types or `unimplemented!()` bodies, especially in test mocks. The cost
depends on how unrelated the choices are, rather than simply on the number of items.

Check whether another context could reuse a provider's complete implementation. A consumer trait
named after an entity rather than an action may group independent choices. If its providers would
not be reusable, implement the trait directly on the context.

Split a component according to the differences between the contexts that need it. Methods with
shared dependencies can become components with reusable providers; methods that must differ can
receive direct impls on each context. See [sizing a
component](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/guides/sizing-a-component.md)
for the procedure and trade-offs.

## A consumer trait is still an ordinary trait

Implement a consumer trait directly when provider reuse is unnecessary. An ordinary
`impl CanGreet for Person { ... }` supports `person.greet()` without wiring. Use the provider
machinery when the capability needs interchangeable implementations.

## Further reference

Consult the online knowledge base for complete macro expansions and accepted syntax:

- [`#[cgp_component]`](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/reference/macros/cgp_component.md)
- [`#[cgp_impl]`](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/reference/macros/cgp_impl.md)
- [`#[cgp_provider]`](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/reference/macros/cgp_provider.md)
- [`#[cgp_new_provider]`](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/reference/macros/cgp_new_provider.md)
- [`IsProviderFor`](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/reference/traits/is_provider_for.md)

These conceptual references explain the consumer/provider split:

- [Consumer and provider traits](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/concepts/consumer-and-provider-traits.md)
- [Bypassing coherence](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/concepts/coherence.md)
- [Impl-side dependencies](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/concepts/impl-side-dependencies.md)

Continue with the related sub-skills for specific tasks:

- [Wiring](wiring.md): Selecting providers for a context.
- [Checking](checking.md): Verifying wiring and diagnosing missing dependencies.
- [Functions and getters](functions-and-getters.md): Reading context values.
- [Higher-order providers](higher-order-providers.md): Composing providers.
