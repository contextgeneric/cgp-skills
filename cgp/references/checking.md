# Checking wiring

Use check traits to verify at compile time that a context's [wiring](wiring.md) is complete.
`check_components!` and `delegate_and_check_components!` report missing dependencies at the wiring
site instead of delaying failure until a component is used.

## Why wiring is lazy

A delegation entry records a provider choice without checking its dependencies. For example, mapping
`GreeterComponent` to `GreetHello` through `DelegateComponent` records an associated type. The
compiler evaluates the provider's `where` bounds only when code uses the [component](components.md).
This deferred evaluation is called lazy wiring.

Lazy wiring permits composition but delays errors. A context's delegation entries and containing
module may compile even when a provider needs a missing field, abstract type, or transitive
dependency. The first consumer-trait call then fails, potentially far from the wiring.

A misnamed field can leave a context with invalid wiring that still compiles. This greeter requires
a `name` field, but the context supplies `first_name`:

```rust
#[cgp_auto_getter]
pub trait HasName {
    fn name(&self) -> &str;
}

#[cgp_component(Greeter)]
pub trait CanGreet {
    fn greet(&self);
}

#[cgp_impl(new GreetHello)]
#[uses(HasName)]
impl Greeter {
    fn greet(&self) {
        println!("Hello, {}!", self.name());
    }
}

#[derive(HasField)]
pub struct Person {
    pub first_name: String, // mismatch: GreetHello needs `name`
}

delegate_components! {
    Person {
        GreeterComponent: GreetHello,
    }
}
```

The block compiles because the consumer trait is not yet used. A later `person.greet()` call fails:
`GreetHello` needs `HasName`, and `Person` lacks the `name` field that would supply it.

## Why the resulting errors are poor

A use-site error can identify the failing provider without exposing its missing dependency. When
Rust checks `Person: CanGreet`, it may report only that `GreetHello` does not implement the provider
trait for `Person`. The competing provider blanket impl suppresses the detailed explanation, so the
missing `name` getter remains hidden. Field names in expanded forms such as `Symbol<…, Chars<…>>`
also make the output harder to read.

Add a check at the wiring site to make the compiler evaluate and report the provider's bounds there.
This gives the failure a predictable location and exposes the dependency that must be supplied.

## How check traits force readable errors

A check trait is a dummy trait whose supertrait is the requirement being asserted. Implementing it
for a context with an empty body compiles only if that requirement holds. The hand-written form is
plain Rust:

```rust
trait CanUsePerson: CanGreet {}
impl CanUsePerson for Person {}
```

This empty impl compiles only when `Person: CanGreet` holds. Placing it beside the wiring catches
the failure early, but checking the consumer trait still produces the same vague provider error. Use
`CanUseComponent` to expose the underlying dependency.

`CanUseComponent<Component, Params>` requires both a delegation entry and a provider that satisfies
`IsProviderFor` for the context. The `IsProviderFor` impl carries the same `where` bounds as the
provider-trait impl. Checking through this marker makes the compiler report the failed dependency,
such as `HasName` or `HasField`. The check macros generate this bound, so you rarely write it
directly.

The failed bound distinguishes absent wiring from unsatisfied dependencies. If `DelegateComponent`
fails, add the missing delegation. If `IsProviderFor` fails, supply the dependency required by the
selected provider.

## Generating checks with `check_components!`

`check_components!` generates check traits from a table of components. It emits a marker trait
aliasing `CanUseComponent` and an empty impl for each component to verify:

```rust
check_components! {
    Person {
        GreeterComponent,
    }
}
```

The generated impl requires `Person: CanUseComponent<GreeterComponent, ()>`. That requirement checks
`GreetHello`'s `IsProviderFor` bounds and reports the missing `name` field at the check site. A
successful build means the assertion passed; the check does not run at runtime.

The check trait is named `__Check{Context}` by default, so `__CheckPerson` here. When two
`check_components!` tables in the same module would collide on that name, override it with
`#[check_trait(Name)]` on the table:

```rust
check_components! {
    #[check_trait(CheckPersonGreeting)]
    Person {
        GreeterComponent,
    }
}
```

Supply concrete parameters when checking a generic component. After the colon, write one parameter
directly or group several into a tuple, matching the `IsProviderFor` `Params` convention. For an
area calculator parameterized by shape, the checks look like this:

```rust
#[cgp_component(AreaOfShapeCalculator)]
pub trait CanCalculateAreaOfShape<Shape> {
    fn area(&self, shape: &Shape) -> f64;
}

check_components! {
    MyApp {
        AreaOfShapeCalculatorComponent: Rectangle,         // one parameter
        TransformCalculatorComponent: (Rectangle, f64),    // two, as a tuple
    }
}
```

Array syntax on either side of the colon expands to the cartesian product, so a set of components
can be checked against a set of parameters in one line. A bracketed value checks one component
against several parameter sets, a bracketed key checks several components against one set, and
bracketing both checks every combination:

```rust
check_components! {
    MyApp {
        AreaOfShapeCalculatorComponent: [Rectangle, Circle],   // one component, two shapes
    }
}
```

This verifies `MyApp: CanCalculateAreaOfShape<Rectangle>` and
`MyApp: CanCalculateAreaOfShape<Circle>` in one entry.

## Checking providers directly with `#[check_providers(...)]`

Use `#[check_providers(...)]` to check individual layers of [higher-order
providers](higher-order-providers.md). It asserts `IsProviderFor` directly on each named provider
instead of asserting `CanUseComponent` on the context. Each provider then has its own diagnostic
location:

```rust
check_components! {
    #[check_trait(CheckScaledRectangleProviders)]
    #[check_providers(
        RectangleAreaCalculator,
        ScaledAreaCalculator<RectangleAreaCalculator>,
    )]
    ScaledRectangle {
        AreaCalculatorComponent,
    }
}
```

The failing lines identify which provider lacks a dependency. A dependency needed only by
`ScaledAreaCalculator` produces an error on the wrapper's line. A missing dependency of
`RectangleAreaCalculator` produces errors on both lines because the wrapper also requires the inner
provider.

## Wiring and checking together with `delegate_and_check_components!`

Use `delegate_and_check_components!` to wire and check a basic context in one block. It delegates
entries as `delegate_components!` would and derives checks for supported keys, helping newcomers
avoid omitted checks. Keep wiring and checking separate for advanced mappings, as explained below:

```rust
#[derive(HasField)]
pub struct MyContext {
    pub name: String,
}

delegate_and_check_components! {
    MyContext {
        NameTypeProviderComponent: UseType<String>,
        NameGetterComponent: UseField<Symbol!("name")>,
    }
}
```

If `MyContext` were missing the `name` field, the derived check on `NameGetterComponent` would fail
to compile and report the missing bound, rather than letting the gap slip through to a later use.

Its check trait is named `__CanUse{Context}` by default, deliberately distinct from
`check_components!`'s `__Check{Context}`, so one of each macro can appear in the same module without
a clash. As with `check_components!`, `#[check_trait(Name)]` overrides the derived name.

Add `#[check_params(...)]` when the delegated component has generic parameters. Delegation can
remain generic, but a check needs concrete parameters. Use the same single-parameter or tuple
convention as `check_components!`:

```rust
delegate_and_check_components! {
    MyApp {
        #[check_params(Rectangle, Circle)]
        AreaOfShapeCalculatorComponent:
            UseDelegate<new AreaOfShapeCalculatorComponents {
                Rectangle: RectangleArea,
                Circle: CircleArea,
            }>,
    }
}
```

The example uses legacy `UseDelegate` dispatch. Prefer `open` for new per-type wiring; see
[wiring](wiring.md). Checks still need concrete parameter sets regardless of how dispatch is wired.
The limits below explain when those checks must be written separately.

Mark an entry `#[skip_check]` when checking it separately, such as with a dedicated
`#[check_providers(...)]` block. `#[skip_check]` and `#[check_params(...)]` are mutually exclusive
on the same entry:

```rust
delegate_and_check_components! {
    ScaledRectangle {
        AreaCalculatorComponent:
            ScaledAreaCalculator<RectangleAreaCalculator>,

        #[skip_check]
        TransformCalculatorComponent:
            ComplexTransform<RectangleAreaCalculator>, // checked in a dedicated check_components! block
    }
}
```

The combined macro derives checks only for component keys in the plain `Component: Provider` form
and its `->` variant. Advanced forms still generate delegation impls but remain silently unchecked.
These include `open` with `@`-path keys, `=>` redirects, and namespace joins. The macro does not
warn that a table is only partly checked.

Per-layer higher-order checks also require a separate check block. They need concrete provider
choices that the combined macro cannot infer from delegation alone.

Keep `delegate_components!` and `check_components!` separate in larger codebases. Standalone checks
support `#[check_providers(...)]`, concrete generic parameters, and opened or namespaced wiring.
Every context's wiring must be checked, whether through the combined macro for simple entries or
explicit checks for advanced ones.

Wire an aggregate provider with `delegate_components!`, never `delegate_and_check_components!`. A
`new SomeComponents { … }` table defines a reusable provider that delegates components to
sub-providers; see [wiring](wiring.md). The combined macro would check whether that provider can use
the components as a context, a role it does not serve.

Checking an aggregate as a context gives misleading results. Providers without impl-side
dependencies accept any context, so the check passes without verifying the actual context. Providers
needing fields or abstract types make it fail against the aggregate. For example, a bundled
`RectangleArea` that reads `width` produces a missing `HasField<Symbol!("width")>` error on
`GeometryComponents`.

Verify the aggregate through a real context that delegates to it. Alternatively, name the aggregate
in `#[check_providers(...)]` to assert `IsProviderFor` for that real context directly.

## Debugging an unsatisfied check

Trace a failed check from the named bound through the provider's dependencies. The error identifies
an impl-side requirement the compiler could not satisfy. If `GreetHello` requires `HasName`, supply
the field or wire the getter component. For a deeper failure, follow each delegation from the
checked component to the provider requiring the missing trait.

Isolate a failing component in a separate `check_components!` block when a large table produces many
errors. Specify its parameters so the output concerns only that component's dependencies. For nested
higher-order providers, use `#[check_providers(...)]` to give each layer its own diagnostic
location.

Satisfy ordinary trait dependencies through ordinary Rust mechanisms. `check_components!` checks
components through `CanUseComponent`; a trait without a component marker or delegation entry cannot
be checked as a wiring entry. Supply its impl, derive, or required `where` bound so the provider's
component check can pass.

## Further reference

Consult the online knowledge base for complete macro syntax and the reasoning behind check traits:

- [`check_components!`](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/reference/macros/check_components.md)
- [`delegate_and_check_components!`](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/reference/macros/delegate_and_check_components.md)
- [Check traits](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/concepts/check-traits.md)
