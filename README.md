This is a more-or-less "by the book" regular expression parser, where "the book" is [Compilers: Principles, Techniques, & Tools (Second Edition)](http://www.amazon.com/Compilers-Principles-Techniques-Tools-2nd/dp/0321486811/). The intended public functionality is provided by `regexp.match(pattern, text)`.

###Use:

Call `regexp.match(pattern, text)`.  `pattern` must be a string representing the regular expression you want to match against, and `text` must be an iterable that yields a series of characters. (For the technically curious, `pattern` is a string instead of an iterable because it needs to look at some characters without consuming them.) `regexp.match` reports whether `text`, *in its entirety*, matches `pattern`.

Call `regexp.search(pattern, text)` if you want to instead detect the presence of any substring of `text` that matches `pattern`.

For a pattern which will be used several times, you can obtain a compiled version by calling `regexp.match_compile(pattern)` (for whole-text matching) or `regexp.search_compile(pattern)` (for substring matching). The returned object will have a `match` or `search` method, as appropriate.

Note: to include a `]` in a character class, it must be escaped with a forward slash: `[ab/]c]` will match any of `a`, `b`, `c`, or `]`.

###Non-features:

- `+` and `?` are not special characters. Use e.g. `aa*` for `a+`, and `(ab|a)` for `ab?`.

- unicode not supported.

- No backreferences. Backreferences are wildly out of scope, as regular languages cannot use them.