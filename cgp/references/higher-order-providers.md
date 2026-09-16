# Higher-order providers

A higher-order provider takes another [provider](components.md) as a type parameter and uses it for
part of its behavior. For example, `ScaledArea<InnerCalculator>` scales an inner result, while
`IterSumArea<InnerCalculator>` sums inner results over a collection. The outer provider defines the
transformation, and the inner provider supplies the calculation.

Providers are zero-sized markers, so nesting them selects implementations at the type level without
adding runtime storage. The examples use CGP v0.8.0 and assume `use cgp::prelude::*;`.

## The shape, and the stray `<Self>`

An inner provider needs a provider-trait bound that names the outer provider’s context. Provider
traits put the context in their leading parameter, so the explicit bound is
`InnerCalculator: AreaCalculator<Self>`. In `#[cgp_impl]`, `Self` refers to the context:

```rust
#[cgp_impl(new ScaledArea<InnerCalculator>)]
impl<InnerCalculator> AreaCalculator
where
    InnerCalculator: AreaCalculator<Self>,
{
    fn area(&self, #[implicit] scale_factor: f64) -> f64 {
        InnerCalculator::area(self) * scale_factor * scale_factor
    }
}
```

`<Self>` supplies the context parameter required by the inner provider trait. At the call site,
`InnerCalculator::area(self)` passes that context explicitly. A call to `self.area()` would use the
context’s consumer trait and its selected provider instead.

## Hiding the friction with `#[use_provider]`

Prefer `#[use_provider]` for inner-provider bounds. Write the provider trait without its leading
context argument, and the attribute inserts that argument into the generated bound:

```rust
#[cgp_impl(new ScaledArea<InnerCalculator>)]
#[use_provider(InnerCalculator: AreaCalculator)]
impl<InnerCalculator> AreaCalculator {
    fn area(&self, #[implicit] scale_factor: f64) -> f64 {
        let base_area = InnerCalculator::area(self);
        base_area * scale_factor * scale_factor
    }
}
```

The attribute turns `InnerCalculator: AreaCalculator` into `InnerCalculator: AreaCalculator<Self>`,
making the examples equivalent. Additional trait arguments retain their order after the inserted
context.

Each attribute accepts one provider type followed by a colon and provider-trait bounds joined by
`+`. Use a separate attribute for each inner provider:

```rust
#[use_provider(A: AreaCalculator)]
#[use_provider(P: PerimeterCalculator)]
```

Do not combine provider bindings with commas. `#[use_provider(A: TraitA, B: TraitB)]` fails with
`expected +` because the parser expects more bounds for `A`. To require several traits on one
provider, write `#[use_provider(Inner: AreaCalculator + PerimeterCalculator)]`. This differs from
the comma-separated lists supported by `#[uses]` and `#[use_type]`. `#[use_provider]` also works on
`#[cgp_fn]`.

`#[use_provider]` changes bounds only; it does not rewrite calls. Invoke the inner provider
explicitly with `InnerCalculator::area(self)`. A bare `#[use_provider(InnerCalculator)]` on an
expression is rejected, and method calls are not converted to provider calls. `self.area()` instead
follows the context’s wiring, which may select a different provider.

## `UseContext` as a default inner provider

Use [`UseContext`](wiring.md) as the default inner provider when a wrapper should reuse the
context’s existing implementation. Declare the provider struct explicitly with a default type
parameter:

```rust
pub struct IterSumArea<InnerCalculator = UseContext>(pub PhantomData<InnerCalculator>);
```

`UseContext` implements provider traits by forwarding to the context’s consumer-trait impl. With the
default above, `IterSumArea` calculates each element through the context’s existing area
implementation. An explicit `IterSumArea<RectangleArea>` selects the inner provider directly and
bypasses that wiring.

The default must appear on an explicit provider struct. A provider declared only through
`#[cgp_impl(new ...)]` does not have a default, so callers must supply its inner provider parameter.

## Not every generic provider is higher-order

A generic parameter makes a provider higher-order only when it represents another provider. A field
tag is a different kind of parameter, as this getter illustrates:

```rust
#[cgp_impl(new GetName<Tag>)]
impl<Tag> NameGetter
where
    Self: HasField<Tag, Value = String>,
{
    fn name(&self) -> &str {
        self.get_field(PhantomData)
    }
}
```

`GetName<Tag>` uses `Tag` only as a `HasField` key. It does not require `Tag` to implement a
provider trait or call it to perform work. A higher-order provider does both through a bound such as
`InnerCalculator: AreaCalculator<Self>`. Without such a bound, `#[use_provider]` does not apply.

## Generic-parameter CGP traits

Generic parameters on a component become provider-trait parameters after the context. This component
adds a `Shape` parameter:

```rust
#[cgp_component(AreaCalculator)]
pub trait CanCalculateArea<Shape> {
    fn area(&self, shape: &Shape) -> f64;
}
```

The generated provider trait is `AreaCalculator<Context, Shape>`. Component parameters retain
declaration order after `Context`, and `IsProviderFor` groups them into its `Params` tuple, using
`()` when the component has none. Lifetime parameters are represented by `Life<'a>`.

A provider can select a concrete parameter in its impl, as in
`impl<Context> AreaCalculator<Context, Rectangle> for RectangleArea`.

## Dispatching on a generic parameter with `open`

Use `open` to select a provider by a component’s generic parameter. For `CanCalculateArea<Shape>`,
the context can assign different providers to `Rectangle` and `Circle` directly in its delegation
table:

```rust
delegate_components! {
    MyApp {
        open AreaCalculatorComponent;

        @AreaCalculatorComponent.Rectangle: RectangleArea,
        @AreaCalculatorComponent.Circle: CircleArea,
    }
}
```

`open AreaCalculatorComponent;` enables per-type entries, with each
`@AreaCalculatorComponent.Key: Provider` selecting a provider for one parameter value. The example
makes `MyApp` use `RectangleArea` for rectangles and `CircleArea` for circles. Add another entry to
support another shape.

`open` uses the `RedirectLookup` impl already generated by `#[cgp_component]`, so it does not need
an additional component attribute. See [wiring](wiring.md) for the complete syntax and shorthands.

### Legacy: `derive_delegate` and `UseDelegate` nested tables

Legacy dispatch uses `#[derive_delegate]` to generate support for a `UseDelegate<Components>`
provider. That provider reads per-type choices from a separate table:

```rust
#[cgp_component(AreaCalculator)]
#[derive_delegate(UseDelegate<Shape>)]
pub trait CanCalculateArea<Shape> {
    fn area(&self, shape: &Shape) -> f64;
}
```

`UseDelegate<Components>` treats `Components` as a `DelegateComponent` table keyed by the selected
parameter, here `Shape`. It forwards methods to the provider assigned to the concrete type. A nested
table defines both the component delegation and the parameter choices:

```rust
delegate_components! {
    MyApp {
        AreaCalculatorComponent:
            UseDelegate<new AreaCalculatorComponents {
                Rectangle: RectangleArea,
                Circle: CircleArea,
            }>,
    }
}
```

`MyApp` delegates the area component to `UseDelegate<AreaCalculatorComponents>`. The inner table
maps `Rectangle` and `Circle` to their providers. This selects the same behavior as the earlier
`open` example, but stores the choices in a separate table.

Prefer `open` for new code. The nested form remains for compatibility and is expected to be
deprecated, though it is still common in existing wiring. See [wiring](wiring.md) for both forms.

Separate `#[derive_delegate]` attributes can generate dispatchers for different parameters. For
example, `UseDelegate<Code>` selects by `Code`, while a user-defined `UseInputDelegate<Input>`
selects by `Input`. Each dispatcher reads its own table and passes the other parameters through. The
custom dispatcher struct uses the same single-parameter shape as `UseDelegate`.

Per-type dispatch can select higher-order providers. An `open` entry or nested table can map each
shape to a different `ScaledArea<...>`.

## Cross-context dependencies through a shared context

A shared context can supply capabilities for operations on several target types. The target is a
generic parameter, while supertraits constrain the context. Here, `Shape` identifies the target and
the context supplies the result’s abstract scalar type:

```rust
#[cgp_component(AreaCalculator)]
#[use_type(HasScalarType.Scalar)]
pub trait CanCalculateAreaOfShape<Shape> {
    fn area_of_shape(&self, shape: &Shape) -> Scalar;
}
```

Shape types do not need to implement capabilities supplied by the common context. `HasScalarType`
lets one application select `f64` and another select a fixed-point type, with all shape providers
using that context’s [abstract type](abstract-types.md).

The context can also supply shared values. `GloballyScaledArea` can read a scale factor through an
implicit argument and apply it to every shape, so the application configures the factor once per
context.

Provider selection is lazy and local to each context. `BaseApp` can select `RectangleArea` for a
shape, while `ScaledApp` selects `GloballyScaledArea<RectangleArea>`. The same capability then has
different behavior without changing the shape type.

Record these choices through `open`, or read them from legacy `derive_delegate`/`UseDelegate` tables
in existing code; see [wiring](wiring.md). Verify each nested provider layer with
`#[check_providers]` in `check_components!` to identify which layer lacks a dependency. See
[checking](checking.md).

## Related constructs

Use these references for the mechanisms behind provider composition:

- [Components](components.md): Consumer and provider traits, including `IsProviderFor`.
- [Wiring](wiring.md): `UseContext`, `open`, and legacy `UseDelegate` tables.
- [Abstract types](abstract-types.md): Shared result types supplied by a context.
- [Type-level primitives](type-level-primitives.md): Tags and other dispatch keys.
- [Checking](checking.md): Verification of individual provider layers.

Consult the online knowledge base for full definitions and syntax:

- [concepts/higher-order-providers.md](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/concepts/higher-order-providers.md)
- [reference/attributes/use_provider.md](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/reference/attributes/use_provider.md)
- [reference/providers/use_delegate.md](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/reference/providers/use_delegate.md)
- [reference/attributes/derive_delegate.md](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/reference/attributes/derive_delegate.md)
