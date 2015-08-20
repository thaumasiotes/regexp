This is a more-or-less "by the book" regular expression parser, where "the book" is [Compilers: Principles, Techniques, & Tools (Second Edition)](http://www.amazon.com/Compilers-Principles-Techniques-Tools-2nd/dp/0321486811/). The intended public functionality is provided by `regexp.match(pattern, text)`.

###Use:

Call `regexp.match(pattern, text)`.  `pattern` must be a string representing the regular expression you want to match against, and `text` must be an iterable that yields a series of characters. (For the technically curious, `pattern` is a string instead of an iterable because it needs to look at some characters without consuming them.)

###Non-features:

- All regular expressions are always represented internally as an [NFA](https://en.wikipedia.org/wiki/Nondeterministic_finite_automaton). When it is anticipated that the same regular expression will be used several times, it is efficient to compile the NFA down to a [DFA](https://en.wikipedia.org/wiki/Deterministic_finite_automaton). However, this is not yet implemented.

- `match` will report whether the provided regular expression matches _the entirety of the input text_. It will not report whether the provided regular expression matches _some substring of the input text_.

- Line anchors (`^` and `$`) are not recognized. However, because the entire input text must be matched, they are superfluous. 

- Some characters can't be legitimately matched: `(`, `)`, `|`, `*`, and `/`. Those characters are syntactically significant.

- On a related note, escape sequences are not yet implemented (though `/` is reserved for future escape sequences).

- Character classes are not yet implemented. If you would have written `[a-f]`, you'll have to write `(a|b|c|d|e|f)` here.

- `+` and `?` are also not special characters. Use e.g. `aa*` for `a+`, and `(ab|a)` for `ab?`.

- No backreferences. Backreferences are wildly out of scope, as regular languages cannot use them.