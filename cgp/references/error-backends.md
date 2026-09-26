# Error backends

The error backends are three opt-in crates that make one concrete type a context's abstract error:
`cgp-error-anyhow` for `anyhow::Error`, `cgp-error-eyre` for `eyre::Report`, and `cgp-error-std` for
`Box<dyn core::error::Error + Send + Sync>`. Each supplies a provider that sets the error type and
providers that raise errors into it and wrap detail onto it. Load this reference when wiring a
backend, choosing a provider for a source type, or reading an error from backend wiring. The
components themselves are covered in [error handling](error-handling.md).

The crates are separate dependencies, not part of the `cgp` crate. Import the wiring keys from
`cgp::core::error` and the providers from the backend crate:

```rust
use cgp::core::error::{ErrorRaiserComponent, ErrorTypeProviderComponent, ErrorWrapperComponent};
use cgp::prelude::*;
use cgp_error_anyhow::{DisplayAnyhowError, RaiseAnyhowError, UseAnyhowError};
```

## The four providers each backend exports

Every backend exports one provider per role, and the roles are the same across the crates. Only
the concrete type and the library call that builds or extends it change:

| Role | anyhow | eyre | std |
|---|---|---|---|
| Set the error type (`ErrorTypeProviderComponent`) | `UseAnyhowError` | `UseEyreError` | `UseBoxedStdError` |
| Raise a standard error intact; wrap a detail | `RaiseAnyhowError` | `RaiseEyreError` | `RaiseBoxedStdError` |
| Raise or wrap any `Debug` value as a message | `DebugAnyhowError` | `DebugEyreError` | `DebugBoxedStdError` |
| Raise or wrap any `Display` value as a message | `DisplayAnyhowError` | `DisplayEyreError` | `DisplayBoxedStdError` |

The last three implement both `ErrorRaiser` and `ErrorWrapper`, so each can be wired to either
component. Each of the three pins the context's error to its crate's type through
`#[use_type(HasErrorType.{Error = ...})]`, so it works only on a context whose error is that type,
usually set by the same crate's type provider. Each crate re-exports its error type as `Error`, for example
`cgp_error_anyhow::Error`.

The raise providers keep the source error: `downcast_ref` still finds it, and it is the first link
of the error chain. The `Debug` and `Display` providers format the value into a new error and keep
only the message, which is how they accept values that are not standard errors at all, such as a
`String` or a `#[derive(Debug)]` struct.

## Wiring a backend

A context wires the type provider, then routes each source type with `open`. This wiring raises a
standard error intact, raises a `String` as a message, and wraps any `'static` detail:

```rust
pub struct App;

delegate_components! {
    App {
        open ErrorRaiserComponent;

        ErrorTypeProviderComponent: UseAnyhowError,
        @ErrorRaiserComponent.std::io::Error: RaiseAnyhowError,
        @ErrorRaiserComponent.String: DisplayAnyhowError,
        ErrorWrapperComponent: RaiseAnyhowError,
    }
}

check_components! {
    App {
        ErrorRaiserComponent: [std::io::Error, String],
        ErrorWrapperComponent: &'static str,
    }
}
```

With this wiring, `App::wrap_error(App::raise_error(std::io::Error::other("disk full")), "while saving")`
prints `while saving` with `{}` and `while saving: disk full` with `{:#}`. A context whose sources
are all standard errors can use one entry without `open`,
`[ErrorRaiserComponent, ErrorWrapperComponent]: RaiseAnyhowError`. The same code works for eyre or
std by swapping the three names.

A context that joins `DefaultNamespace` wires the same providers by path, because the error
components register under `@cgp.core.error`:

```rust
delegate_components! {
    App {
        namespace DefaultNamespace;

        @cgp.core.error.ErrorTypeProviderComponent: UseAnyhowError,
        @cgp.core.error.ErrorRaiserComponent.std::io::Error: RaiseAnyhowError,
        @cgp.core.error.ErrorRaiserComponent.String: DisplayAnyhowError,
    }
}
```

## Routing each source type

Route each source or detail type to the provider that keeps the most information about it. The
table uses each crate's own provider names:

| Source or detail | Raise with | Wrap with |
|---|---|---|
| A standard error, such as `std::io::Error` or `ParseIntError` | `Raise…` | — |
| `String`, `&'static str`, or another message | `Display…` | `Display…` or `Raise…` |
| A type with only `Debug` | `Debug…` | `Debug…` |
| A borrowed detail, such as `&'a str` | — | `Display…` or `Debug…` |
| The context's own error, raised again | the generic `RaiseFrom` or `ReturnError` | — |

Prefer `Display…` for a message, because `Debug…` quotes a string: raising `"bad input"` produces the
message `"bad input"` with the quotation marks. Neither `anyhow::Error`, `eyre::Report`, nor a boxed
`dyn Error` is itself a standard error, so re-raising the context's own error needs `RaiseFrom`,
which accepts it through the reflexive `From<T> for T`.

The raise providers require `E: StdError + Send + Sync + 'static`, and the anyhow and eyre raise
providers used as wrappers require `Detail: Display + Send + Sync + 'static`. The `'static` bound
rejects a detail borrowed from a function argument; wire the wrapper to `Display…` or `Debug…`,
which copy the detail into a string. `RaiseBoxedStdError`'s wrapper needs only `Detail: Display`.

## When a backend is not needed

The generic providers in `cgp-error-extra` already cover two of the four roles.
`UseType<anyhow::Error>` sets the error type exactly as `UseAnyhowError` does, and `RaiseFrom`
raises a standard error exactly as `RaiseAnyhowError` does. A context that only raises standard
errors and never wraps them needs no backend. A context whose errors form a closed set is often
better served by its own error enum with `UseType<AppError>` and `RaiseFrom`, which keeps every
variant matchable.

A backend adds what the generic providers lack. Its wrappers attach a detail to the error, where the
generic `DiscardDetail` drops it and the generic `DebugError`/`DisplayError` forward it to
`CanWrapError<String>`. Its `Debug…`/`Display…` providers build the concrete error from a string
directly, so they can serve as the context's `String` provider.

## Per-crate behavior

The crates differ in a few facts that affect wiring and output:

- **`cgp-error-anyhow`** is `no_std` and builds anyhow without its `std` feature. `{:?}` prints the
  outermost message followed by a `Caused by:` list.
- **`cgp-error-eyre`** needs `std`, because eyre does. It enables eyre's `auto-install` feature, so
  eyre's default handler is installed on the first report; install `color-eyre` or another handler
  with `eyre::set_hook` before raising anything, since `set_hook` returns an error once a handler
  exists. Reports carry no `Location:` section: the crate leaves `track-caller` off, because the
  recorded location would always be a line inside the backend. The default handler appends a
  backtrace to `{:?}` when `RUST_BACKTRACE` or `RUST_LIB_BACKTRACE` is set.
- **`cgp-error-std`** is `no_std` and needs only `alloc`. Its formatting raisers produce a
  `StringError`, and every wrapper produces a `WrapError`, which returns the wrapped error from
  `source()`. `WrapError` prints only its detail with `{}`, so a reporter that walks `source()`
  prints each message once, and prints the whole chain joined by `": "` with `{:#}` or `{:?}`.

These behaviors describe the `cgp` source on `main`. The 0.8.0-alpha crates on crates.io differ:
their `cgp-error-eyre` panics on every report unless a hook has been installed with
`eyre::set_hook`, their `WrapError` prints its source twice when the chain is walked, and their
`RaiseBoxedStdError` cannot be wired as a wrapper. Check the host's `Cargo.lock`; if it resolves the
published 0.8.0-alpha backends, install an eyre hook at startup or build against `cgp` `main`
through `[patch.crates-io]`.

## Diagnosing backend wiring

Most backend errors come from a source routed to a provider whose bounds it does not meet. List the
source types in a `check_components!` block and run `cargo cgp check`; each mistake below then fails
at the check entry:

- **A message through the raise provider.** `ErrorRaiserComponent: RaiseAnyhowError` checked for
  `String` fails with `E0277`, "the trait bound `String: Error` is not satisfied". Route `String` to
  `DisplayAnyhowError`.
- **A raiser without its error type.** Wiring `RaiseAnyhowError` with no `ErrorTypeProviderComponent`
  entry fails with `[CGP-E001]`, whose root cause `[CGP-E107]` names the missing
  `ErrorTypeProviderComponent`. Add `UseAnyhowError`.
- **Two backends on one context.** `UseBoxedStdError` with `RaiseAnyhowError` fails with `E0271`
  tagged `[CGP-E017]`: the abstract `Error` is `Box<dyn Error + Send + Sync>` where `Error` is
  expected. The expected `Error` is `anyhow::Error` with its path removed. Use the raiser from the
  crate that sets the type.
- **A `String` routed back to itself.** `@ErrorRaiserComponent.String: DebugError`, using the generic
  `DebugError`, fails with `E0275` tagged `[CGP-E010]`, because `DebugError` for `String` needs
  `CanRaiseError<String>` again. Route `String` to a backend's `Display…` or `Debug…` provider.
- **A borrowed detail.** A provider that uses `for<'a> CanWrapError<&'a str>` on a context wired to
  `ErrorWrapperComponent: RaiseAnyhowError` fails with a plain `E0477`, "the type `&'a str` does not
  fulfill the required lifetime". Wire the wrapper to `DisplayAnyhowError`.

When a downstream project depends on a backend from crates.io, test it against a local change
through `[patch.crates-io]`, overriding `cgp` together with the backend. Patching the backend alone
leaves two copies of the CGP crates in the graph, and the wiring fails with `E0599` and a rustc note
about multiple versions of `cgp_error`.

## Related documentation

Consult the online knowledge base for each provider's exact bounds and output, the tests that pin
them, and the per-crate open issues:

- [The error backends project](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/projects/error/README.md)
- [Choosing a backend and routing errors](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/projects/error/guides/choosing-a-backend.md)
- [Debugging backend wiring](https://github.com/contextgeneric/cgp-knowledge-base/blob/main/projects/error/guides/debugging.md)
