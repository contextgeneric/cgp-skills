# Wiring

Wiring selects the provider for each component on a context. A [component](components.md) separates
the consumer trait callers use from the provider trait implementations supply; the context's
type-level table connects them. `delegate_components!` defines that table, and generated blanket
impls resolve calls through it at compile time. This reference describes CGP v0.8.0 and assumes
`use cgp::prelude::*;`.

## The table: `DelegateComponent`

`DelegateComponent<Key>` maps a key type to a delegate type on `Self`:

```rust
pub trait DelegateComponent<Key: ?Sized> {
    type Delegate;
}
```

The table consists of trait impls and contains neither methods nor runtime data. Implementing
`DelegateComponent<Key>` sets the entry; projecting `<Self as DelegateComponent<Key>>::Delegate`
reads it. Rust's coherence rules permit at most one applicable impl for each `Self` and `Key`, so a
lookup has an unambiguous result.

Component entries map `…Component` markers to provider types. The compiler resolves these
associations and emits statically dispatched calls, without a runtime table or vtable lookup.

A component entry connects the context to the selected provider through generated blanket impls.
Once the provider's dependencies are satisfied, the context implements the consumer trait and calls
such as `app.greet()` forward to that provider.

`DelegateComponent` can also use arbitrary keys, such as shape types or tags. A
[higher-order provider](higher-order-providers.md) can read such a dispatch table without each key
naming a component.

## `delegate_components!`: populating the table

Use `delegate_components!` to generate wiring impls from `Key: Provider` entries. This table selects
`RectangleArea` for `Rectangle`'s area component:

```rust
#[derive(HasField)]
pub struct Rectangle {
    pub width: f64,
    pub height: f64,
}

delegate_components! {
    Rectangle {
        AreaCalculatorComponent: RectangleArea,
    }
}
```

With this wiring, `rect.area()` resolves to `RectangleArea` when its dependencies are met. The
target before the braces identifies the context or intermediary provider table carrying the entries.

Use a bracketed key list when several components share a provider. The macro emits a separate entry
for each marker:

```rust
delegate_components! {
    Rectangle {
        [
            AreaCalculatorComponent,
            PerimeterCalculatorComponent,
        ]: RectangleGeometry,
        GreeterComponent: GreetHello,
    }
}
```

The geometry entries both select `RectangleGeometry`, while `GreeterComponent` selects `GreetHello`.
The bracketed form has the same effect as listing each geometry entry separately.

Add `new` before the target to declare its struct along with its wiring. This is the usual way to
define an **aggregate provider**, a zero-sized provider that delegates a group of components to
other providers:

```rust
delegate_components! {
    new GeometryComponents {
        AreaCalculatorComponent: RectangleArea,
        PerimeterCalculatorComponent: RectanglePerimeter,
    }
}
```

Other contexts can reuse the aggregate by delegating the grouped components to it. For example,
`delegate_components! { App { [AreaCalculatorComponent, PerimeterCalculatorComponent]: GeometryComponents } }`
gives `App` the geometry providers selected above.

Wire aggregate providers with plain `delegate_components!` and verify them through the contexts that
use them. `delegate_and_check_components!` would check the aggregate as though it were its own
context, which does not test its intended use. See [checking](checking.md) for aggregate-provider
checks.

A leading generic list applies the wiring to a family of types. For example,
`delegate_components! { <T> MyContext<T> { … } }` defines entries for every `MyContext<T>`.

### What the macro generates

Each entry generates a `DelegateComponent` impl for lookup and an `IsProviderFor` impl for
dependency propagation. The rectangle entry's lookup impl is:

```rust
impl DelegateComponent<AreaCalculatorComponent> for Rectangle {
    type Delegate = RectangleArea;
}
```

The provider blanket impl reads `DelegateComponent` to find the chosen provider. The companion
`IsProviderFor` impl propagates that provider's requirements, allowing checks to identify missing
transitive [impl-side dependencies](components.md). Defining the wiring alone does not prove those
dependencies are satisfied; verify the context with [checking](checking.md).

## Explicit delegation: what wiring effectively does

A direct consumer impl can perform the same forwarding as a wiring entry. The following
implementation calls `RectangleArea`'s provider-trait method and passes `self` as its context:

```rust
impl CanCalculateArea for Rectangle {
    fn area(&self) -> f64 {
        <RectangleArea as AreaCalculator<Self>>::area(self)
    }
}
```

`AreaCalculatorComponent: RectangleArea` selects the same call path through generated blanket impls.
It covers every method in the trait without manual forwarding and also generates
dependency-propagation support. Prefer the table form; use explicit forwarding to explain the
mechanism or deliberately bypass the table for one trait.

## Direct implementation of a consumer trait

Implement the consumer trait directly when its behavior is specific to one context and a reusable
provider adds little. The consumer trait remains an ordinary Rust trait:

```rust
impl CanGreet for Person {
    fn greet(&self) {
        println!("Hello, I am {}", self.name);
    }
}
```

`person.greet()` calls this implementation directly. Do not also wire the same component on
`Person`: the wiring's blanket impl would supply a second consumer impl and conflict with the direct
one.

## `UseContext`: routing a provider trait back to the consumer trait

`UseContext` adapts a context's existing consumer-trait implementation into a provider. It is a
zero-sized marker used at the type level:

```rust
pub struct UseContext;
```

`UseContext` forwards from the provider trait to the consumer trait, reversing the usual delegation
direction. For each component, `#[cgp_component]` generates an impl like this one, which calls the
context's existing `CanGreet` implementation:

```rust
impl<Context> Greeter<Context> for UseContext
where
    Context: CanGreet,
{
    fn greet(context: &Context) {
        Context::greet(context)
    }
}
```

Use `UseContext` as an inner provider when a [higher-order provider](higher-order-providers.md)
should defer to the context's existing implementation. Higher-order providers often make it the default
type argument, allowing wiring to name an explicit inner provider only when that choice should
differ.

Never delegate a component to `UseContext` when that delegation is the context's only implementation
of the component. Resolution would require the consumer trait to obtain the provider trait, then
require the same consumer trait again. The cycle produces an overflow or unsatisfied-bound error. An
inner `UseContext` call must resolve through an independently available implementation.

## Other providers you will see in tables: `WithProvider` and `UseDefault`

`WithProvider` adapts a lower-level provider to a named component, while `UseDefault` selects a
component's default method bodies. Both are zero-sized providers that can appear in ordinary wiring
entries.

`WithProvider<Inner>` connects a general provider mechanism to a component-specific interface. For
example, [`FieldGetter`](functions-and-getters.md) reads a tagged field without knowing the getter
component's name, and [`TypeProvider`](abstract-types.md) supplies a type without naming an
abstract-type component. The adapter forwards the component's operation to that mechanism.

Common aliases avoid spelling out the adapter:

- **`WithField` and `WithFieldRef`:** Adapt a field getter to a getter component.
- **`WithType` and `WithDelegatedType`:** Adapt a type provider to an abstract-type component.
- **`WithContext`:** Adapt the context's own implementation.

An entry such as `NameGetterComponent: WithField<…>` selects the field getter named inside the
adapter.

`UseDefault` supplies a provider name for a component whose methods all have default bodies. The
author writes an empty `#[cgp_impl(UseDefault)]` impl to accept those defaults, then wires the
component to `UseDefault`. The macros do not automatically implement every component for it. A
concrete context can also accept consumer-trait defaults through an empty direct impl.

## Dispatching a component per type with `open`

Use `open` to select a provider per type argument of a generic component. It stores the per-type
entries in the context's own table. For a `CanCalculateArea<Shape>` component, this wiring chooses
the area provider by `Shape`:

```rust
delegate_components! {
    MyApp {
        open AreaCalculatorComponent;

        @AreaCalculatorComponent.Rectangle: RectangleArea,
        @AreaCalculatorComponent.Circle: CircleArea,
    }
}
```

Place `open` before plain `Component: Provider` mappings or the macro will fail to parse. A single
component may use `open AreaCalculatorComponent;` or `open { AreaCalculatorComponent };`. Open
several with `open { A, B };`.

Each `@Component.Key: Provider` entry selects a provider for one dispatch type. The example resolves
`CanCalculateArea<Rectangle>` through `RectangleArea` and `CanCalculateArea<Circle>` through
`CircleArea`, provided their dependencies are satisfied.

Bracketed path groups select alternatives for one segment and allow more segments afterward.
`@AreaCalculatorComponent.[Rectangle, Circle]: SomeProvider` wires both shapes to one provider.
Groups on several segments expand to every combination, as in
`@app.[FooComponent, BarComponent].[u64, String]: P`.

Braced groups select complete path tails and must end the path. Their alternatives may differ in
length and may nest. For example,
`@app.{ErrorRaiserComponent.{&'static str, String}, ErrorWrapperComponent}: RaiseFrom` covers three
routes. Appending `.bool` after the closing brace is invalid and produces `expected ':'`.

Put per-key generic parameters before the dispatch type.
`@SomeComponent.<'a, T> &'a T: SomeProvider` selects `SomeProvider` for references of that form
across all `'a` and `T`.

`open` uses the `RedirectLookup` impl generated by `#[cgp_component]` and does not require
`#[derive_delegate]`. It is suited to a context defining its own per-type wiring.

Use full namespace paths when the context joins a namespace that registers the component with
`#[prefix(...)]`. Opening that same component at its bare name conflicts with its namespace route.
See [namespaces](namespaces.md) for shared tables, prefixed paths, and the `namespace` statement.

### Legacy: `UseDelegate` nested tables

Legacy `UseDelegate` wiring stores the per-type entries in a separate table. The nested `new` form
declares that table inside the provider argument:

```rust
delegate_components! {
    MyApp {
        AreaCalculatorComponent: UseDelegate<new AreaCalculatorComponents {
            Rectangle: RectangleArea,
            Circle: CircleArea,
        }>,
    }
}
```

The macro emits a standalone `AreaCalculatorComponents` table and sets the outer delegate to
`UseDelegate<AreaCalculatorComponents>`. The resulting choices match the `open` example: `Rectangle`
uses `RectangleArea`, and `Circle` uses `CircleArea`. The difference is that the choices reside in
the separate table.

Prefer `open` for new per-type wiring. The legacy form remains for compatibility and is expected to
be deprecated and removed. See [higher-order providers](higher-order-providers.md) when reading its
dispatch mechanics in existing code.

## Related constructs

Consult these references for the constructs used in wiring:

- [Components](components.md): Consumer and provider traits, markers, and generated impls.
- [Checking](checking.md): Verifying wiring and transitive dependencies.
- [Namespaces](namespaces.md): Shared tables and path-based dispatch.
- [Higher-order providers](higher-order-providers.md): `UseContext`, provider composition, and legacy `UseDelegate` dispatch.

## Further reference

The knowledge base provides complete definitions and expansions:

- [`delegate_components!`](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/reference/macros/delegate_components.md).
- [`DelegateComponent`](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/reference/traits/delegate_component.md).
- [`UseContext`](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/reference/providers/use_context.md).
