# Modern idioms: reading and modernizing CGP

Prefer modern CGP syntax in new code, and keep explicit forms for cases the shorthand cannot
express. This reference pairs older forms with their modern equivalents so you can read generated
code and revise existing implementations. The examples assume `use cgp::prelude::*;` and describe
CGP v0.8.0.

Modern syntax makes providers resemble ordinary trait impls and expresses dependencies through
attributes. The macros still expand to explicit traits, bounds, and provider calls, so those forms
remain useful when reading expansions.
[The exceptions below](#when-the-explicit-forms-are-still-right) identify cases that need explicit
syntax.

Each comparison explains the rule connecting the forms. Preserve the original bounds and behavior
when applying it; field access and dispatch rewrites also require checking the context's fields and
wiring.

## Provider shape: `#[cgp_impl]` over the raw provider forms

Write providers with [`#[cgp_impl]`](components.md) to use `self`, `Self`, and consumer-style method
signatures. The lower-level `#[cgp_provider]` and `#[cgp_new_provider]` forms take an explicit
context parameter and a receiver such as `context: &Context`. This older implementation reads the
rectangle's fields through `HasField`:

```rust
#[cgp_new_provider]
impl<Context> AreaCalculator<Context> for RectangleArea
where
    Context: HasField<Symbol!("width"), Value = f64>,
    Context: HasField<Symbol!("height"), Value = f64>,
{
    fn area(context: &Context) -> f64 {
        *context.get_field(PhantomData::<Symbol!("width")>)
            * *context.get_field(PhantomData::<Symbol!("height")>)
    }
}
```

The modern form uses `#[cgp_impl]` and [`#[implicit]`](functions-and-getters.md) arguments to read
the same fields:

```rust
#[cgp_impl(new RectangleArea)]
impl AreaCalculator {
    fn area(&self, #[implicit] width: f64, #[implicit] height: f64) -> f64 {
        width * height
    }
}
```

`#[cgp_impl]` expands through the lower-level provider macros, so their explicit form still appears
in generated code. Write that form directly only when you need a provider-trait impl or bounds the
shorthand cannot express.

## Context parameter: omit `for Context`

Omit `for Context` from a `#[cgp_impl]` header unless the context needs an explicit name or bound.
The macro supplies its reserved context parameter. For example, this implementation names the
context only to require `HasDimensions`:

```rust
#[cgp_impl(new RectangleArea)]
impl<Context> AreaCalculator for Context
where
    Context: HasDimensions,
{
    fn area(&self) -> f64 { self.width() * self.height() }
}
```

The bare header and `#[uses]` express the same requirement without naming the context:

```rust
#[cgp_impl(new RectangleArea)]
#[uses(HasDimensions)]
impl AreaCalculator {
    fn area(&self) -> f64 { self.width() * self.height() }
}
```

## Dependencies: `#[uses]` and `#[use_provider]` over hand-written `where`

Declare context capabilities with [`#[uses(...)]`](functions-and-getters.md) and inner-provider
requirements with [`#[use_provider(...)]`](higher-order-providers.md). These attributes generate
[impl-side dependencies](components.md): `#[uses(CanCalculateArea)]` adds `Self: CanCalculateArea`,
and `#[use_provider(Inner: AreaCalculator)]` adds `Inner: AreaCalculator<Self>`. The explicit form
names those bounds in a `where` clause:

```rust
#[cgp_impl(new ScaledArea<InnerCalculator>)]
impl<Context, InnerCalculator> AreaCalculator for Context
where
    Context: HasField<Symbol!("scale_factor"), Value = f64>,
    InnerCalculator: AreaCalculator<Context>,
{
    fn area(&self) -> f64 { /* ... */ }
}
```

The modern form moves the inner-provider bound to an attribute and the field requirement to an
implicit argument:

```rust
#[cgp_impl(new ScaledArea<InnerCalculator>)]
#[use_provider(InnerCalculator: AreaCalculator)]
impl<InnerCalculator> AreaCalculator {
    fn area(&self, #[implicit] scale_factor: f64) -> f64 { /* ... */ }
}
```

Use one comma-separated `#[uses]` attribute for several capabilities, as in
`#[uses(CanQueryUserBalance, CanRaiseHttpError<ErrNotFound, String>)]`. It accepts `where`-clause
bounds, though the simple `Trait<Params>` form is preferred. For an abstract-type equality such as
`Self: HasErrorType<Error = AppError>`, prefer the
[`#[use_type]` equality form](#abstract-types-use_type-over-supertrait--selftype). Keep explicit
bounds for traits whose associated types you would not import, such as `Iterator<Item = u8>`.

Give each inner provider its own `#[use_provider]` attribute. A comma-separated list of
provider-and-trait pairs does not parse. To require several traits on one provider, join its bounds
with `+`.

## Field reads: `#[implicit]` over a getter trait

Prefer [`#[implicit]`](functions-and-getters.md) arguments for fields on the provider's own context.
Each argument names the field and the local value, and a plain `&T` borrows without cloning. This
also applies when several providers read the same field. The following getter-based implementation
can use implicit arguments instead:

```rust
#[cgp_auto_getter]
pub trait HasDimensions {
    fn width(&self) -> &f64;
    fn height(&self) -> &f64;
}

#[cgp_impl(new RectangleArea)]
#[uses(HasDimensions)]
impl AreaCalculator {
    fn area(&self) -> f64 { self.width() * self.height() }
}
```

Implicit arguments read `width` and `height` directly from the context:

```rust
#[cgp_impl(new RectangleArea)]
impl AreaCalculator {
    fn area(&self, #[implicit] width: f64, #[implicit] height: f64) -> f64 {
        width * height
    }
}
```

Use `#[cgp_auto_getter]` when the access needs a trait of its own:

- **Another type's field:** Require a getter on that type, such as `Request: HasBasicAuthHeader<Self>`.
- **Named capability:** Expose an accessor that other code requires through a trait bound.
- **Abstract field type:** Infer a getter's associated return type from the field.

Reserve `#[cgp_getter]` for choosing the getter's source field per context through wiring. Ordinary
reads from the provider's own context should use implicit arguments.

## Abstract types: `#[use_type]` over supertrait + `Self::Type`

Import abstract types with [`#[use_type]`](abstract-types.md) and use their bare aliases. The
attribute adds the owning trait as a supertrait on `#[cgp_component]` or as an impl-side bound on
`#[cgp_impl]` and `#[cgp_fn]`. It also rewrites each alias to its fully qualified associated-type
path. This applies to built-in types such as `Error`, which the explicit form qualifies as
`Self::Error`:

```rust
#[cgp_component(Loader)]
pub trait CanLoad: HasErrorType {
    fn load(&self, path: &str) -> Result<String, Self::Error>;
}
```

The attribute supplies the supertrait and qualifies `Error` for you:

```rust
#[cgp_component(Loader)]
#[use_type(HasErrorType.Error)]
pub trait CanLoad {
    fn load(&self, path: &str) -> Result<String, Error>;
}
```

Keep a definition's own associated types qualified as `Self::Assoc`. The rewrite applies only to
imported bare identifiers. A handler declaring `type Output` therefore writes
`Result<Self::Output, Error>` when `Error` is imported.

Combine type imports in one comma-separated attribute, as in
`#[use_type(HasUserIdType.UserId, HasCurrencyType.Currency, HasErrorType.Error)]`. Use braces for
several types from one trait: `#[use_type(HasFooType.{Foo, Bar})]`. Repeated attributes behave
identically, but the combined form keeps the imports together.

Use the trailing `in Context` clause to import an associated type from another type. For example,
`#[use_type(HasUserIdType.UserId in App)]` adds `App: HasUserIdType` and rewrites `UserId` to
`<App as HasUserIdType>::UserId`. It replaces the explicit bound and qualified type in this getter:

```rust
#[cgp_auto_getter]
pub trait HasLoggedInUser<App>
where
    App: HasUserIdType,
{
    fn logged_in_user(&self) -> &Option<App::UserId>;
}
```

The imported alias makes the getter's return type shorter:

```rust
#[cgp_auto_getter]
#[use_type(HasUserIdType.UserId in App)]
pub trait HasLoggedInUser<App> {
    fn logged_in_user(&self) -> &Option<UserId>;
}
```

The attribute supplies `App: HasUserIdType`, so the generic parameter needs only the name `App`.

Import abstract types explicitly even when a capability's supertrait already supplies the bound. If
`CanCreateFoo` extends `HasFooType`, use `#[uses]` for the capability and `#[use_type]` for its
type:

```rust
#[cgp_fn]
#[uses(CanCreateFoo)]
#[use_type(HasFooType.Foo)]
fn bar(&self) -> Foo { self.create_foo(42) }
```

The older form relies on the transitive supertrait to resolve `Self::Foo`:

```rust
#[cgp_fn]
#[uses(CanCreateFoo)]
fn bar(&self) -> Self::Foo { self.create_foo(42) }
```

The explicit import makes the type dependency visible. It adds an already implied `Self: HasFooType`
bound and rewrites the bare `Foo`.

Use the equality form `#[use_type(Trait.{Assoc = Type})]` to constrain an abstract type to a
concrete one. It replaces an explicit bound such as `Self: HasErrorType<Error = AppError>` in this
provider:

```rust
#[cgp_impl(new DisplayHttpError)]
impl<Code, Detail> HttpErrorRaiser<Code, Detail>
where
    Self: HasErrorType<Error = AppError>,
    Code: IsStatusCode,
    Detail: Display,
{
    fn raise_http_error(_code: Code, detail: Detail) -> AppError { /* ... */ }
}
```

The equality moves into the attribute while the other generic bounds stay in the `where` clause:

```rust
#[cgp_impl(new DisplayHttpError)]
#[use_type(HasErrorType.{Error = AppError})]
impl<Code, Detail> HttpErrorRaiser<Code, Detail>
where
    Code: IsStatusCode,
    Detail: Display,
{
    fn raise_http_error(_code: Code, detail: Detail) -> AppError { /* ... */ }
}
```

The attribute emits `Self: HasErrorType<Error = AppError>` and rewrites any bare `Error`. This
example continues to name the concrete `AppError` directly.

The equality's right-hand side can also refer to imported aliases. For example,
`#[use_type(HasPasswordType.Password, HasHashedPasswordType.{HashedPassword = Password})]` equates
`HashedPassword` with `<Self as HasPasswordType>::Password`. Nested aliases work too:
`#[use_type(HasDbType.Db, HasTransactionType.{Transaction = Tx<Db>})]` produces
`Self: HasTransactionType<Transaction = Tx<<Self as HasDbType>::Db>>`.

The equality form is supported on `#[cgp_impl]` and `#[cgp_fn]`, where it produces an impl-side
bound. `#[cgp_component]` rejects it.

## Supertraits: `#[extend]` over native `:` syntax

Add capability supertraits with [`#[extend(...)]`](functions-and-getters.md). It generates the same
bound as native `pub trait CanDoX: Supertrait` syntax, while distinguishing a public dependency from
the impl-side dependencies declared with `#[uses]`. The explicit form places `HasName` after the
trait name:

```rust
#[cgp_component(Greeter)]
pub trait CanGreet: HasName {
    fn greet(&self) -> String;
}
```

The attribute form declares the same `HasName` supertrait:

```rust
#[cgp_component(Greeter)]
#[extend(HasName)]
pub trait CanGreet {
    fn greet(&self) -> String;
}
```

Use `#[extend]` for capabilities and `#[use_type]` for abstract types named in the signature. The
latter also rewrites the type aliases. In `#[cgp_fn]`, ordinary `where` clauses describe impl-side
dependencies, so use `#[extend]` to add a supertrait.

## Per-type dispatch: `open` and namespaces over `UseDelegate`

Use [`open`](wiring.md) or a [namespace](namespaces.md) to choose a provider per generic argument.
Both use the `RedirectLookup` impl generated by `#[cgp_component]`. The older
[`UseDelegate`](higher-order-providers.md) pattern stores its per-type entries in a separate table:

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

The `open` form stores the same provider choices directly on the context:

```rust
delegate_components! {
    MyApp {
        open AreaCalculatorComponent;

        @AreaCalculatorComponent.Rectangle: RectangleArea,
        @AreaCalculatorComponent.Circle: CircleArea,
    }
}
```

Components dispatched through `open` or namespaces do not need
`#[derive_delegate(UseDelegate<Param>)]`. That attribute generates the provider support for legacy
`UseDelegate` tables. Some CGP error and handler components retain it for compatibility.

Choose `open` for a context's own per-type wiring. Use a namespace when several contexts should
share a reusable table or inherit common routes.

## When the explicit forms are still right

Keep explicit syntax where it expresses a requirement the preferred shorthand does not cover:

- **Other trait bounds:** Keep explicit bounds such as `Iterator<Item = u8>` or `From<X>` when they are not abstract-type imports. Use `#[use_type]` for abstract-type equalities.
- **Named context:** Write `impl<Context> Trait for Context` when a lifetime or higher-ranked bound requires the name. Use `#[cgp_impl(Self)]` with an explicit concrete context for a direct consumer impl.
- **Configurable getter:** Use `#[cgp_getter]` when wiring must choose the source field per context.
- **Explicit provider impl:** Write the raw provider-trait form when the shorthand cannot express the implementation.
- **Local associated type:** Keep `Self::Output` qualified when the definition declares `Output` itself.

For routine providers, dependencies, and field reads, use the modern forms above.

## Reading pre-0.7 code: renamed and removed names

Pre-0.7 code may use names that current CGP has removed or renamed. Replace `#[cgp_context]` with
`delegate_components!` and the relevant derive or getter machinery. The abstract-type provider trait
formerly named `ProvideType` is now `TypeProvider`.

Check an unfamiliar name against the current exports and the online knowledge base's changelog or
reference before copying it. A missing prelude export may require an explicit import; it does not by
itself prove that the name was removed.

## Related sub-skills

Consult the owning reference for full syntax and expansion details:

- [Components](components.md): Provider forms and generated traits.
- [Functions and getters](functions-and-getters.md): Implicit fields, `#[uses]`, and `#[extend]`.
- [Abstract types](abstract-types.md): Type imports and equality bounds.
- [Higher-order providers](higher-order-providers.md): Inner-provider dependencies.
- [Wiring](wiring.md) and [namespaces](namespaces.md): Per-type dispatch.
- [Macro grammar](macro-grammar.md): Accepted forms and expansion rules.
- [Modularity hierarchy](modularity-hierarchy.md): Choosing how much CGP a problem needs.
