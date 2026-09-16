# Namespaces

A namespace shares component wiring across contexts through a named lookup trait. It can bind common
providers and redirect other lookups to paths that each context supplies. This gives CGP reusable
presets resolved entirely at compile time.

Use a namespace when contexts would otherwise repeat the same wiring. A context joins the shared
table, then supplies entries at paths left unbound by that namespace. A namespace does not support
arbitrary overrides: directly binding a key it already resolves creates overlapping impls. The
examples describe CGP v0.8.0 and assume `use cgp::prelude::*;`.

## What a namespace is

A namespace is a trait with a `Delegate` associated type, implemented for each key it resolves.
Joining it generates forwarding impls on the context; the namespace itself is never instantiated. A
binding supplied by the namespace applies to every joining context.

Path-based redirects let contexts customize shared wiring without redefining existing bindings. A
path is a type-level list of symbols and types. The namespace can route a component marker to a path
while leaving the provider at that path for the context to choose.

## Defining a namespace with `cgp_namespace!`

Define a namespace with `cgp_namespace!` and use `new` to generate its lookup trait and backing
marker struct. The body resembles a `delegate_components!` table. This namespace maps both `String`
and `u64` to `ShowWithDisplay`:

```rust
cgp_namespace! {
    new DefaultShowComponents {
        [String, u64]: ShowWithDisplay,
    }
}
```

Use `:` to bind a provider and `=>` to redirect a lookup. The example binds `ShowWithDisplay`
directly. An entry such as `FooProviderComponent => @MyFooComponent` instead looks up
`@MyFooComponent` in the consulting table, where another entry supplies the provider.

Namespace bodies share the [wiring grammar](macro-grammar.md) of `delegate_components!`. The entries
generate `impl Namespace<__Table__> for Key` rather than `DelegateComponent` impls. An `open C;`
statement is equivalent to `C => @C,`. Use the `: ParentNamespace` header for inheritance.

Legacy nested-table values also parse in a namespace body. The macro emits their inner tables as
separate structs and impls, so joining contexts share the nested dispatch table. Retain this form
when reading existing `UseDelegate` wiring; use modern path-based dispatch for new code.

Name a parent after the namespace header's colon to inherit its entries. The child may add routes at
keys the parent leaves unbound:

```rust
cgp_namespace! {
    new ExtendedNamespace: DefaultNamespace {
        @cgp.core.error =>
            @app,
    }
}
```

`ExtendedNamespace` inherits `DefaultNamespace` and redirects the `@cgp.core.error` prefix to
`@app`. The redirect applies to the subtree under that prefix, allowing the context to place its
error providers under `@app`.

Omit the braces when the namespace does not add entries:
`cgp_namespace! { new AppNamespace: DefaultNamespace }` has the same expansion as an empty braced
body. `delegate_components!` always requires its braces.

### What the macro generates

With `new`, the macro generates a backing struct and a lookup trait parameterized by the consulting
table:

```rust
pub struct __MyNamespaceComponents;

pub trait MyNamespace<__Table__> {
    type Delegate;
}
```

Each entry implements the namespace trait for its key. A `:` entry sets `Delegate` to the provider;
a `=>` entry sets it to `RedirectLookup` with the destination path. For
`FooProviderComponent => @MyFooComponent`, the generated impl is:

```rust
impl<__Table__> MyNamespace<__Table__> for FooProviderComponent {
    type Delegate = RedirectLookup<__Table__, PathCons<MyFooComponent, Nil>>;
}
```

Inheritance adds a blanket impl forwarding keys resolved by the parent. Child entries must not
overlap that impl. Their position in the macro body does not give them precedence over a parent
binding.

## Attaching components and joining namespaces

Register a component's route with `#[prefix(@path in Namespace)]` on its
[`#[cgp_component]`](components.md) trait. For example, [`HasErrorType`](error-handling.md) uses
`#[prefix(@cgp.core.error in DefaultNamespace)]`, so joining contexts inherit the route for the
error-type component. Registration supplies a redirect; a provider must still be bound at its
destination.

The generated impl appends the component marker to the prefix. For a `BarProviderComponent`
registered under `@MyBarComponent` in `MyNamespace`, the route is:

```rust
impl<__Components__> MyNamespace<__Components__> for BarProviderComponent {
    type Delegate = RedirectLookup<
        __Components__,
        PathCons<MyBarComponent, PathCons<BarProviderComponent, Nil>>,
    >;
}
```

Join a namespace with `namespace MyNamespace;` inside `delegate_components!`. The context then
resolves the namespace's registered keys through its lookup trait. Assuming `ShowImplComponent` is
registered under `@test` and the namespace leaves the destination unbound, this context selects the
provider for `u64`:

```rust
delegate_components! {
    AppA {
        namespace DefaultNamespace;

        @test.ShowImplComponent.u64:
            ShowWithDisplay,   // supplies the provider for u64
    }
}
```

The namespace header generates a blanket `DelegateComponent` impl forwarding keys through
`DefaultNamespace<AppA>`. It also generates `IsProviderFor` forwarding so [checks](checking.md) can
report provider dependencies. The direct path entry supplies the provider reached by the component's
redirect.

Direct entries must not overlap bindings supplied by the namespace. If the namespace already binds
the destination path through a `:` entry or `#[default_impl]`, a direct context entry for that path
conflicts with the forwarding impl and Rust reports `E0119`. Keep configurable destinations unbound
in the namespace; the same restriction applies to a child namespace redefining a parent's key.

Check inherited components with a standalone `check_components!`. Joining through
`delegate_and_check_components!` also checks supported direct entries, but it does not derive checks
for all components supplied by the namespace. See [checking](checking.md).

## Paths with `Path!`

Use `Path!` to turn a dotted, `@`-prefixed address into a type-level path. Namespace entries use the
same syntax to identify lookup destinations:

```rust
type ErrorRoute = Path!(@app.error.ErrorRaiserComponent);
// PathCons<Symbol!("app"),
//     PathCons<Symbol!("error"),
//         PathCons<ErrorRaiserComponent, Nil>>>
```

A single lowercase identifier becomes a `Symbol!` string unless it names a primitive type.
Capitalized names such as `ErrorRaiserComponent` remain types. The macro nests these segments in
`PathCons` cells ending in `Nil`. Paths are usually written directly in namespace entries or
`#[prefix]` attributes, which perform this conversion without an explicit `Path!` call.

## The `RedirectLookup` provider

`RedirectLookup<Components, Path>` resolves a provider from a table using a path key. Ordinary
component delegation looks up the component marker; this [provider](components.md) looks up `Path`
in `Components` and forwards to the resulting delegate. The table and lookup key can therefore vary
independently.

The macros normally generate `RedirectLookup` for you. Every `#[cgp_component]` supplies an impl of
its provider trait for it, and `=>` entries and `#[prefix]` attributes use it as their delegate. For
a component without type parameters, the generated forwarding has this shape:

```rust
impl<__Context__, __Components__, __Path__> Greeter<__Context__>
    for RedirectLookup<__Components__, __Path__>
where
    __Components__: DelegateComponent<__Path__>,
    <__Components__ as DelegateComponent<__Path__>>::Delegate: Greeter<__Context__>,
{
    fn greet(__context__: &__Context__) -> String {
        <__Components__ as DelegateComponent<__Path__>>::Delegate::greet(__context__)
    }
}
```

The redirected delegate must implement the requested provider trait for the context. Components with
type parameters append those parameters to the path before looking it up, which makes the
destination depend on the generic arguments and enables per-type dispatch.

## Default resolution: the `DefaultNamespace` family

The default-resolution traits select a `Delegate` from a key and a consulting table.
`DefaultNamespace<Components>` uses the implementing type as its key. `DefaultImpls1<T, Components>`
and `DefaultImpls2<T1, T2, Components>` add key parameters. A common use implements
`DefaultImpls1<Component, Components>` for a value type to register that component's per-type
default:

```rust
pub trait DefaultNamespace<Components> {
    type Delegate;
}

pub trait DefaultImpls1<T, Components> {
    type Delegate;
}
```

`DefaultNamespace` is the built-in namespace used by component prefixes and
`namespace DefaultNamespace;`. Register a per-type provider with
`#[default_impl(T in DefaultImpls1<Component>)]` on its impl. This emits
`impl<Components> DefaultImpls1<Component, Components> for T { type Delegate = Provider; }`. Import
`DefaultImpls1` and `DefaultImpls2` from `cgp::core::component`; they are outside the prelude.

Registration omits the provider's impl-side bounds. Requirements introduced by `#[uses]` or
`#[use_type]` are checked when the provider is used, so abstract-type dependencies do not prevent
registration.

A `#[default_impl]` key may also be a path. For example,
`#[default_impl(@app.GreeterComponent in AppNamespace)]` binds that destination directly in
`AppNamespace`, allowing a joining context to resolve it without a `for` loop. Use a separate
attribute for each registration.

The registering crate must own the namespace trait or satisfy Rust's ownership rules for the key. An
owned component marker can be registered into a foreign namespace, but a prefixed `PathCons` key is
foreign, so its registration belongs in the namespace's crate.

Use a `for` loop to import per-type defaults into the context's path table. In this example, assume
the registry supplies defaults for other types but leaves `u64` unregistered; the direct entry
supplies that type's provider:

```rust
delegate_components! {
    App {
        namespace DefaultNamespace;

        for <T, Provider> in DefaultImpls1<ShowImplComponent> {
            @test.ShowImplComponent.T: Provider,
        }

        @test.ShowImplComponent.u64:
            ShowWithDisplay, // supplies u64, which the registry leaves unregistered
    }
}
```

The loop generates wiring bounded by
`T: DefaultImpls1<ShowImplComponent, App, Delegate = Provider>`. The direct `u64` entry is valid
only if it does not overlap that bound. It does not override a matching registry impl.

A loop can also import a namespace table. For example,
`for <T, Provider> in DefaultShowComponents { … }` reads the entries defined earlier for `String`
and `u64`. An optional `where` clause, as in `for <T, Provider> in Table where T: Clone { … }`, adds
bounds to every generated impl and narrows which types the loop wires.

## Defining a preset once, reusing it across contexts

Design a preset by binding shared choices and leaving configurable destinations unbound. A library
can publish that namespace, and applications can join it or inherit from it while supplying the
remaining providers. This keeps common wiring in one place and application choices on each context.

A preset uses the namespace machinery directly; CGP does not require a separate `cgp_preset!`
construct. Trait resolution handles inheritance and redirection at compile time, without a runtime
lookup table.

## Related constructs

Read these references for the constructs used by namespaces:

- [Wiring](wiring.md): `DelegateComponent` tables and context delegation.
- [Components](components.md): Component markers and generated traits.
- [Checking](checking.md): Verifying inherited providers and dependencies.
- [Type-level primitives](type-level-primitives.md): `Path!`, `PathCons`, and symbol segments.
- [Higher-order providers](higher-order-providers.md): Per-type dispatch and provider composition.

## Further reference

Consult the online knowledge base for complete syntax and expansions:

- [Namespaces](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/concepts/namespaces.md).
- [`cgp_namespace!`](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/reference/macros/cgp_namespace.md).
- [`RedirectLookup`](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/reference/providers/redirect_lookup.md).
- [`Path!`](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/reference/macros/path.md).
