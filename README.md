# vars_matcher library
## Matching and ratio methods for program code names  

All main matching methods are instance methods of the class **VarsMatcher**, while all of them returns an instance of MatchingBlocks contains all the matches according to the algorithm and parameters of the matching method, includes the ratio between the two compared names, the list of the matches between them, etc. 

The ratio's formula depends on the method, as described in the project document (MM: TODO). 

## Classes

### *class* vars_matcher.*Var*

A class contains all the needed data about a variable:
- **name**: its original name (string)
- **words**: list of the words the variable built from
- **norm_name**: variable's name after normalization
- **separator**: a special character that doesn't exist in both variables, for internal use while searching for a match.

### *class* vars_matcher.VarMatch

A class contains the data about one match:

- **i**: the index of the match in the first variable
- **j**: the index of the match in the second variable
- **k**: the length of the match
- **d**: the distance between the variables in this match

### *class* vars_matcher.VarsMatcher

The main library's class, that calculates the matches. It contains:

- **var_1**: a Var class with all data about the first variable
- **Var_2**: a Var class with all data about the second variable
- **case_sensitivity**: a Boolean (default: false), that set if to save the case when transforming the variables to 
their “normal form”
- **word_separator**: a string that contains all the characters in the variables that are used as a separator between 
words (default: “_”)
- **support_camel_case**: a Boolean that set if to relate to moving from a little letter to a big one marks on a new 
word, or not (default: true)
- **numbers_behavior**: a number from the set \{0,1,2\} that set how to relate to digits in the variable: 
  - 0 means relate to the number as a separate word.
  - 1 means remove them from the normalized variable. 
  - 2 means leaving them in their place (default: 0).
- **literal_comparison**: a Boolean, that true means relate the variable as is as normalized (default: false).

### *class* vars_matcher.MatchingBlocks

A class contains all the data about the matches:

- **a**: the first variable
- **b**: the second variable
- **cont_type**: a Boolean that indicates if the match is necessarily continuous or not
- **ratio**: the calculated ratio between the two variables

## Methods

### *VarsMatcher*.ordered_match(min_len=2)

A method that works like Sequence Matcher algorithm - finding at first the longest match and continue recursively 
on both sides of the match, but every time that there are more than one match with the same length - this method finds 
the longest matches **that maximize the ratio between the variables**.

Note: this method uses Dynamic Programming for calculate that. As a result, the running time is about $`m^{2}n^{2}`$ while m and n are number of letters in the first and second variables, respectively.

#### Parameters: 

***min_len*** **: int, default 2** 
    
&nbsp;&nbsp;&nbsp;&nbsp;Minimum length of letters that will be related as a match.

#### Return value:

MatchingBlocks class.


### *VarsMatcher*.ordered_words_match(min_word_match_degree=1, prefer_num_of_letters=False)

A method that finds the matches that maximize the ratio between the variables words, while requires - after finding a match with maximal number of letters, the searching for other matches will be done separately on the left sides and the right sides of the match.

Note: this method uses dynamic programming for calculate that. As a result, the running time is about m^{2}n^{2}, while m and n are number of words in the first and second variables, respectively.

#### Parameters: 

***min_word_match_degree*** : **float, default 1**

&nbsp;&nbsp;&nbsp;&nbsp;Set the minimum ratio between two words to be intended as a match (1 means perfect match).

***prefer_num_of_letters*** : **bool, default False**

&nbsp;&nbsp;&nbsp;&nbsp; Set if to prefer - when searching after the “longest match” - the match with more letters (True) or with more words (False).


### *VarsMatcher*.ordered_semantic_match(min_word_match_degree=1, prefer_num_of_letters=False, meaning_distance=1)

A method that finds the matches that maximize the ratio between the variables words, while requires - after finding a match with maximal number of letters, the searching for other matches will be done separately on the left sides and the right sides of the match.

Note: this method uses dynamic programming for calculate that. As a result, the running time is about m^{2}n^{2}, while m and n are number of words in the first and second variables, respectively.

#### Parameters: 

***min_word_match_degree*** : **float, default 1**

&nbsp;&nbsp;&nbsp;&nbsp;Set the minimum ratio between two words to be intended as a match (1 means perfect match).

***prefer_num_of_letters*** : **bool, default False**

&nbsp;&nbsp;&nbsp;&nbsp;Set if to prefer - when searching after the “longest match” - the match with more letters (True) or with more words (False).

***• meaning_distance*** : **float, default 1**

&nbsp;&nbsp;&nbsp;&nbsp;Set the distance to relate to synonyms and singular/plural words (because Edit Distance isn't relevant for them).


### *VarsMatcher*.unordered_match(min_len=2)

A method that searches for matches between the variables, but enables also “cross matches” after finding one match, i.e. after finding one of the longest match, every match between the remained letters will be legal.

#### Parameters: 

#### Parameters: 

***min_len*** **: int, default 2** 
    
&nbsp;&nbsp;&nbsp;&nbsp;Minimum length of letters that will be related as a match.

#### Return value:

MatchingBlocks class.


### *VarsMatcher*.unordered_words_match(min_word_match_degree=1, prefer_num_of_letters=False)

A method that searches for matches between the names in a variables, and enables also “cross matches” after finding one match, i.e. after finding one of the longest match, every match between the remained letters will be legal. In addition, it enables not perfect matching between words - depend on a parameter the user set.

#### Parameters: 

***min_word_match_degree*** : **float, default 1**

&nbsp;&nbsp;&nbsp;&nbsp;Set the minimum ratio between two words to be intended as a match (1 means perfect match).

***prefer_num_of_letters*** : **bool, default False**

&nbsp;&nbsp;&nbsp;&nbsp; Set if to prefer - when searching after the “longest match” - the match with more letters (True) or with more words (False).


### *VarsMatcher*.unordered_semantic_match(min_word_match_degree=1, prefer_num_of_letters=False, meaning_distance=1)

A method that searches for matches between the names in a variables, and enables also “cross matches” after finding one match, i.e. after finding one of the longest match, every match between the remained letters will be legal. In addition, it enables not perfect matching between words - depend on a parameter the user set, and enable match between synonyms and singular/plural words.

#### Parameters: 

***min_word_match_degree*** : **float, default 1**

&nbsp;&nbsp;&nbsp;&nbsp;Set the minimum ratio between two words to be intended as a match (1 means perfect match).

***prefer_num_of_letters*** : **bool, default False**

&nbsp;&nbsp;&nbsp;&nbsp;Set if to prefer - when searching after the “longest match” - the match with more letters (True) or with more words (False).

***• meaning_distance*** : **float, default 1**

&nbsp;&nbsp;&nbsp;&nbsp;Set the distance to relate to synonyms and singular/plural words (because Edit Distance isn't relevant for them).


### *VarsMatcher*.unedit_match(min_len=2)

A method (that may be useful in curious cases) that after each match removes it from the variables, and concatenating both sides of it. (As a result, letters in the left side with those from right side of the match could build a new word).

#### Parameters: 

***min_len*** **: int, default 2** 
    
&nbsp;&nbsp;&nbsp;&nbsp;Minimum length of letters that will be related as a match.

#### Return value:

MatchingBlocks class.
