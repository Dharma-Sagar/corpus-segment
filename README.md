# corpus-segment
corpus segmentation using botok

## syntax for corpus segmentation
- additions: `+` at the end of words
- removals: `/` at the end of words
- span: to add/remove more than one word, add `(` at the beginning of the span

joining affixed particles:

ex: to join `རྣམ་པ -ར་ དག་པ་` in a single word, simply do `(རྣམ་པ་ -ར་ དག་པ་+`. the script will turn it into `རྣམ་པར་དག་པ་`.

double adjustments:

in case like `བདག་གཅེས་ འཛིན་` where you want to 1. remove `བདག་གཅེས་` from the wordlist and then put together `གཅེས་འཛིན་`, follow the following syntax:

`(བདག་ {གཅེས་/ འཛིན་}`