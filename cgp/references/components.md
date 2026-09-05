# Components

A CGP **component** is the bundle that `#[cgp_component]` generates from one trait, so that *using* a capability and *implementing* it become separate, swappable things. This is the central reference. Read it first.

## What a component is

A component is a single trait definition compiled into a small machine: a **consumer trait** that callers invoke, a **provider trait** that implementations target, a `…Component` marker key, and the blanket impls that connect them. An ordinary Rust trait conflates using a capability with implementing it. The type you call `.area()` on is the same type that supplies the `area` body, and Rust's coherence rules then allow only one implementation per type. A component breaks that conflation. That is what lets many independent implementations of the same capability coexist, and what lets you implement a capability for a type you do not own.

The split is produced by `#[cgp_component]`, applied to an ordinary trait. Throughout this file the running examples are the greeting component (`CanGreet` / `Greeter` / `GreetHello`, on a `Person`) and the area component (`CanCalculateArea` / `AreaCalculator` / `RectangleArea`, on a `Rectangle`). Assume `use cgp::prelude::*;` in every snippet. The CGP version is v0.8.0.

## What `#[cgp_component(Greeter)]` generates

Applying the macro to a consumer trait produces the consumer trait, the provider trait, two blanket impls, and the marker struct. Start from the trait, naming the provider trait in the attribute argument:

```rust
#[cgp_component(Greeter)]
pub trait CanGreet {
    fn greet(&self);
}
```

The **consumer trait** is emitted unchanged. This is the self-style trait callers use (`CanDoX`), so a caller writes `person.greet()` exactly as with any trait:

```rust
pub trait CanGreet {
    fn greet(&self);
}
```

The **provider trait** is the same interface with `Self` moved out into an explicit leading `Context` type parameter and every `self`/`Self` rewritten to `context`/`Context`. It is named in noun form (`SomethingDoer`, or `…Provider` when no noun fits). It carries an `IsProviderFor` supertrait that captures the component, the context, and a `Params` tuple of any extra type parameters, which is `()` when there are none:

```rust
pub trait Greeter<Context>:
    IsProviderFor<GreeterComponent, Context, ()>
{
    fn greet(context: &Context);
}
```

A provider trait is implemented not for the context but for a dedicated zero-sized **provider** struct, a type-level marker that is never instantiated and carries no runtime value. Because a provider implements `Greeter<Context>` for *its own* struct over a generic `Context`, the orphan and overlap rules never bite. So `GreetHello`, `GreetGoodbye`, and any number of further providers for the same component can all exist at once. See [bypassing coherence](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/concepts/coherence.md) (online) for why moving `Self` to a parameter sidesteps the rules, and [modularity hierarchy](modularity-hierarchy.md) for how far to take the split.

## How the two traits connect

Two generated blanket impls bridge the consumer and provider sides. Together they make `person.greet()` resolve to a chosen provider without the caller naming it. Read them as the wiring machinery. You never write them.

The **consumer blanket impl** says that any context implementing the provider trait *for itself* gets the consumer trait. It forwards `context.greet()` to `Context::greet(self)`:

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

The **provider blanket impl** lets any provider that delegates this component inherit the provider trait from whatever it delegates to. The delegation is a type-level table lookup through `DelegateComponent`, keyed on the `GreeterComponent` marker:

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

These examples use readable names for clarity. The emitted code uses reserved identifiers, `__Context__` for the context parameter (overridable) and `__Provider__` for the provider parameter, chosen so they never clash with a user's own type names.

## Wiring is the table lookup that ties it all together

**Wiring** supplies the delegation the provider blanket impl reads. It makes a context into a type-level table whose entry for each component names the chosen provider. With the greeting component wired, the chain resolves end to end. `person.greet()` goes through the consumer impl to `Person` implementing the provider trait for itself, which goes through the provider impl to the table entry, landing on the selected provider's `greet`. Swapping the table entry is the only change needed to swap behavior. No caller is touched.

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

The full table grammar, including per-value dispatch and presets, lives in [wiring](wiring.md). This file shows only the single-entry form needed to make the resolution concrete.

## Why `IsProviderFor` exists

`IsProviderFor` is an empty marker trait that rides along on every provider trait as a supertrait. Its only job is to make a missing dependency produce a readable error. A provider lists what it needs from the context in a `where` clause. When that clause is unmet, the bare question "does this provider implement the provider trait?" yields only "trait not implemented", because the provider blanket impl is also a candidate and Rust suppresses its detailed reasoning whenever more than one impl could apply.

`IsProviderFor` is the independent path that un-hides the real reason. The macros implement it for a provider under *exactly the same* `where` bounds as the provider trait. Because that impl is the only candidate, with no competing blanket, Rust commits to it and prints the precise unsatisfied constraint. So an `IsProviderFor` not implemented error means the provider trait is not implemented, and the named bound is the missing dependency. The trait is generated and consumed entirely by the macros. You observe it in errors, and you never write it.

```rust
#[diagnostic::on_unimplemented(
    note = "You need to add `#[cgp_provider({Component})]` on the impl block for CGP provider traits"
)]
pub trait IsProviderFor<Component, Context, Params: ?Sized = ()> {}
```

## Writing providers

A provider can be written at several levels of sugar over the same machinery, and `#[cgp_impl]` is the one to reach for. The lower forms exist for when the native provider-trait shape is wanted explicitly, and they are what `#[cgp_impl]` desugars to.

The lowest form is `#[cgp_provider]`, applied to a provider-trait impl written directly on a provider struct. It passes the impl through unchanged and generates the matching `IsProviderFor` impl from the same `where` clause, so the dependency set can never drift. The provider struct must already exist:

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

That expands to the impl above plus the empty marker impl carrying the same bound, which surfaces a missing `HasDimensions` as a named error:

```rust
impl<Context> IsProviderFor<AreaCalculatorComponent, Context, ()> for RectangleArea
where
    Context: HasDimensions,
{}
```

The optional attribute argument overrides the component type, which otherwise defaults to the provider trait's name plus a `Component` suffix. Pass it explicitly only when the trait name does not follow that convention.

The middle form is `#[cgp_new_provider]`. It is identical to `#[cgp_provider]` but also declares the provider struct, folding `pub struct RectangleArea;` into the same block. Use it when introducing a fresh provider, so you need not write the struct separately. A generic provider yields a struct with a `PhantomData` field over its parameters.

The preferred form is `#[cgp_impl]`. It lets you write the provider in **consumer-style syntax**, keeping `self`, `Self`, and the consumer trait's method signatures, and it rewrites the block into the provider-trait shape. The provider name moves into the attribute argument instead of the `Self` position, a leading `new` keyword declares the struct, and you may omit `for Context` entirely and let the macro insert the context parameter:

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

The one rule this convenience must not let you forget: inside a `#[cgp_impl]` block, `self` and `Self` mean the **context**, never the provider struct. The provider has no runtime value, so the macro rewrites every `self` to the context value and every `Self` to the context type. Those are the only things that exist when the method runs.

`#[cgp_impl]` desugars to `#[cgp_provider]`, or to `#[cgp_new_provider]` when `new` is given. The block above is equivalent to writing the context out by hand and lowering it:

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

The receiver `&self` became `__context__: &__Context__`, where the receiver identifier is the snake-cased context name wrapped in double underscores, and `Self` in the `where` clause became the context type. When you write `for Context` explicitly, that name is used instead of `__Context__`. Do so when you need to bound or refer to the context readably.

## Impl-side dependencies

A provider states what it needs from the context as bounds in its `where` clause. Those bounds are **impl-side dependencies**, constraints the consumer trait never exposes. `CanCalculateArea` declares only `area`, while `RectangleArea` requires `Context: HasDimensions`. A caller bounding on `CanCalculateArea` never sees `HasDimensions`, so the requirement stays one level down and does not cascade through transitive callers. This is dependency injection through the `where` clause. Any context satisfying the bound gains the capability, and the wiring satisfies each bound by resolving it through the same context. See [impl-side dependencies](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/concepts/impl-side-dependencies.md) (online) for the full treatment, and [functions and getters](functions-and-getters.md) for the value-injection forms (`#[implicit]` arguments and getters) that read fields off the context through the same mechanism.

## Which items belong in one component

**A component trait may declare as many items as any Rust trait. The question is not how many items, but how many independent *choices* they represent.** Everything in one component is answered by one provider. So group the items a single provider choice decides together, and separate the ones different choices decide. Most application capabilities are one decision and therefore one method, which is why single-method components dominate. The count follows from the principle rather than being a limit.

Two groupings of several items are right rather than merely allowed. **A method plus the associated type it produces** belong together, because a provider that answers *how* also answers *what comes back*. That is why CGP's own `CanCompute`, `CanHandle`, and `CanProduce` each declare `type Output` beside their method, and why a `CanQueryDatabase` with `type Row` and `query` is good design. Splitting `Row` out would let a context pair the Postgres querier with the SQLite row type. **A getter component grouping several field reads** also belongs together, because a getter is answered by its own method name rather than by a strategy. One `UseFields` provider satisfies every method at once, and there is nothing to split. The trade-off is that `UseField` and `WithProvider` are emitted only for a single-method getter trait, so a getter wired to a differently named field needs its own component.

Grouping items that answer to *different* choices has costs, and the cost rises with how unrelated they are rather than with the count. Every provider carries the **union of its methods' dependencies**, so a capability one method needs is imposed on all of them and on every context wiring that provider. A [higher-order provider](higher-order-providers.md) must **implement every item**, forwarding the ones it has no opinion about. A single-decision component wraps in four lines, while a wrapper over an entity trait is mostly passthrough that grows with every method added. And a context or provider that needs part of the surface must **still answer all of it**, which in practice means placeholder associated types and `unimplemented!()` bodies, most often in mock contexts written for tests.

Simple checks catch a component that has grown past one decision. A consumer trait named after a noun rather than a verb usually holds several. And if no provider for the trait could ever be reused *whole* by a second context, the machinery is not paying for itself, so implement the trait directly on the concrete context instead, per the section below. To break one up, split along the axis on which the contexts you want differ. The methods whose dependencies are shared across those contexts become components with reusable providers, and the ones that must differ get a direct impl on each context. The full procedure and its costs are in [sizing a component](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/guides/sizing-a-component.md) (online).

## A consumer trait is still an ordinary trait

A consumer trait can also be implemented directly on a context, exactly like a vanilla Rust trait, when code reuse across providers is not the goal. The consumer/provider split is a superset of ordinary traits, not a replacement. The provider machinery is what you opt into when a capability needs more than one implementation, and skipping it costs nothing for the simple case. You write `impl CanGreet for Person { ... }` as usual, and `person.greet()` resolves to that direct impl with no wiring involved.

## Further reference

For the full expansion and accepted syntax of each macro, see the online docs:
[`#[cgp_component]`](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/reference/macros/cgp_component.md),
[`#[cgp_impl]`](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/reference/macros/cgp_impl.md),
[`#[cgp_provider]`](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/reference/macros/cgp_provider.md),
[`#[cgp_new_provider]`](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/reference/macros/cgp_new_provider.md),
and
[`IsProviderFor`](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/reference/traits/is_provider_for.md).
For the concepts behind the split, see
[consumer and provider traits](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/concepts/consumer-and-provider-traits.md),
[bypassing coherence](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/concepts/coherence.md),
and
[impl-side dependencies](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/cgp/concepts/impl-side-dependencies.md).
For sibling sub-skills, see [wiring](wiring.md), [checking](checking.md),
[functions and getters](functions-and-getters.md), and
[higher-order providers](higher-order-providers.md).
