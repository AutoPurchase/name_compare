# names_matcher library
## Matching and ratio methods for program code names  

Program code contains functions, variables, and data structures that are represented by names. To promote human understanding, these names should describe the role and use of the code elements they represent. But the names given by developers show high variability, reflecting the tastes of each developer, with different words used for the same meaning or the same words used for different meanings. This makes comparing names hard. A precise comparison should be based on matching identical words, but also take into account possible variations on the words (including spelling and typing errors), reordering of the words, matching between synonyms, and so on. 

To facilitate this we developed a library of comparison functions specifically targeted to comparing names in code. The different functions calculate the similarity between names in different ways, so a researcher can choose the one appropriate for his specific needs. All of them share an attempt to reflect human perceptions of similarity, at the possible expense of lexical matching.

The ratio's formula was described in the project document (MM: TODO). 


## User Manual

1. install namecompare library (by running "**pip install namecompare**").
2. In the head of the python file type "**import names_matcher**".
3. Generate **names_matcher.NamesMatcher** object, set names to compare, and run comparison function (as detailed below)... 
 

Example:
    
    import names_matcher
    print(names_matcher.NamesMatcher('FirstLightAFire', 'LightTheFireFirst').ordered_words_match())

Output:

    var_1: ['first', 'light', 'a', 'fire'], var_2: ['light', 'the', 'fire', 'first']
    Ratio: 0.4
    Matches:
	    var_1[1:2], var_2[0:1], length: 1, local ratio: 1.0, partial ratio: 0.2:
		    ['light'] vs. 
		    ['light']
	    var_1[3:4], var_2[2:3], length: 1, local ratio: 1.0, partial ratio: 0.2:
		    ['fire'] vs. 
		    ['fire']




## Classes

### *class* *Var*

A class contains all the needed data about a variable:
- **name**: its original name (string).
- **words**: list of the words the variable built from.
- **norm_name**: variable's name after normalization.
- **separator**: a special character that doesn't exist in both variables, for internal use while searching for a match.

### *class* OneMatch

A class contains the data about one match:

- **i**: the index of the match in the first variable.
- **j**: the index of the match in the second variable.
- **k**: the length of the match.
- **l**: when the comparison based on words, this variable contains number of letters in these words.
- **r**: when the comparison based on words, this variable contains the ratio of the match.

### *class* MatchingBlocks

A class contains the data about all the matches.
This class has a converter to string that prints readable summary about its matches.

  #### Constants:
    LETTERS_MATCH = 0
    WORDS_MATCH = 1

    CONTINUOUS_MATCH = 0
    DISCONTINUOUS_MATCH = 1

- **name_1**: the first string or list of words to be compared.
- **name_2**: the second string or list of words to be compared.
- **ratio**: the total ratio between the two strings of lists of words.
- **matching_type**: *LETTERS_MATCH* for string matching, and *WORDS_MATCH* for list-of-words matching.
- **cont_type**: *CONTINUOUS_MATCH* for matching only between continuous letters (so if minimum match is 2 letters - two uncontinuous letters will never be related as a one match), and DISCONTINUOUS_MATCH for *unedit_match()* function, that after matching a sub-string, its two sides attached together (so one letter from left side and one from right side will be related as two continuous letters).
- **continuity_heavy_weight**: the weight to let to continuity. False means relating to the "glue" between all the letters or words as one component, while True means relating each "glue" as one element. This "glue" means: for letting to match of some continuous elements heavy weight than the same number of single elements, we give a weight also to the "space" between letters, that will be received only when the elements of both sides of this space matches in one match. The weight of that is set by this variable.     

### *class* NamesMatcher

#### Constants:
    NUMBERS_SEPARATE_WORD = 0
    NUMBERS_IGNORE = 1
    NUMBERS_LEAVE = 2

This is the main library's class, that calculates the matches. It contains:

- **name_1**: a Var class with all data about the first variable
- **name_2**: a Var class with all data about the second variable
- **case_sensitivity**: a Boolean (default: false), that set if to save the case when transforming the variables to their “normal form”
- **word_separator**: a string that contains all the characters in the variables that are used as a separator between words (default: “_”)
- **support_camel_case**: a Boolean that set if to relate to moving from a little letter to a big one marks on a new word, or not (default: true)
- **numbers_behavior**: variable that set how to relate to digits in the variable (default: *NUMBERS_SEPARATE_WORD*): 
  - *NUMBERS_SEPARATE_WORD* means relate to the number as a separate word.
  - *NUMBERS_IGNORE* means remove them from the normalized variable. 
  - *NUMBERS_LEAVE* means leaving them in their place.
- **stop_words**: list of Stop Words that could be ignored when comparing words. If this parameter is None, the list will be the default one:


    [a, are, as, at, be, but, by, for, if, not, of, on, so, the, there, was, were]

## Methods

### *NamesMatcher*.set_name_1(name)
Set the first name to be compared.

### *NamesMatcher*.def get_name_1()
Get the first name to be compared.

### *NamesMatcher*.set_name_2(name)
Set the second name to be compared.

### *NamesMatcher*.get_name_2()
Get the second name to be compared.

### *NamesMatcher*.set_names(name_1, name_2)
Set the both names to be compared.

### *NamesMatcher*.get_norm_names()
Get the both name after normalization (removing spaces, replacing to small letters - if *case_sensitivity*==False, etc.).

### *NamesMatcher*.get_words()
Get the both name after dividing to words (depends on *word_separators* value).

### *NamesMatcher*.set_case_sensitivity(case_sensitivity)
Set *case_sensitivity* value. 

### *NamesMatcher*.get_case_sensitivity()
Get *case_sensitivity* value.

### *NamesMatcher*.set_word_separators(word_separators)
Set *word_separators* value.

### *NamesMatcher*.get_word_separators()
Get *word_separators* value.

### *NamesMatcher*.set_support_camel_case(support_camel_case)
Set *support_camel_case* value.

### *NamesMatcher*.get_support_camel_case()
Get *support_camel_case* value.

### *NamesMatcher*.set_numbers_behavior(numbers_behavior)
Set *numbers_behavior* value.

### *NamesMatcher*.get_numbers_behavior()
Get *numbers_behavior* value.

### *NamesMatcher*.set_stop_words(stop_words)
Set *stop_words* value.

### *NamesMatcher*.get_stop_words(stop_words)
Get *stop_words* value.

### *NamesMatcher*.edit_distance(enable_transposition=False)
A function that uses *strsimpy* library to calculate the Edit Distance between *NamesMatcher*.name_1 and *NamesMatcher*.name_2. 

If *enable_transposition*==False, it uses Levenshtein distance, else it uses Damerau distance.

#### Return value:

Integer value.


### *NamesMatcher*.normalized_edit_distance(enable_transposition=False)
A function that uses *strsimpy* library to calculate the Edit **Distance** between *NamesMatcher*.name_1 and *NamesMatcher*.name_2, and normalizes the result to be in the range [0,1] (by dividing the distance by number of letters in the longest name).

If *enable_transposition*==False, it uses Levenshtein distance, else it uses Damerau distance.

#### Return value:

Float value.


### *NamesMatcher*.difflib_match_ratio()
A function that uses *difflib.SequenceMatcher* to calculate the **ratio** between *NamesMatcher*.name_1 and *NamesMatcher*.name_2.

#### Return value:

*MatchingBlocks* object.


### *NamesMatcher*.ordered_match(min_len=2, continuity_heavy_weight=False)

  A method that works like Sequence Matcher algorithm - finding at first the longest match and continue recursively on both sides of the match, but every time that there are more than one match with the same length - this method finds the longest matches **that maximize the ratio between the variables**.
  
  **Note:** this method uses Dynamic Programming for calculate that. As a result, the running time is about $`m^{2}n^{2}`$ while m and n are number of letters in the first and second variables, respectively.


#### Parameters: 

***min_len*** **(int, default 2):** 
Minimum length of letters that will be related as a match.

***continuity_heavy_weight*** **(boolean, default False):** the weight to let to continuity. False means relating to the "glue" between all the letters or words as one component, while True means relating each "glue" as one element. This "glue" means: for letting to match of some continuous elements heavy weight than the same number of single elements, we give a weight also to the "space" between letters, that will be received only when the elements of both sides of this space matches in one match. The weight of that is set by this variable.

#### Return value:

*MatchingBlocks* object.


### *NamesMatcher*.unordered_match(min_len=2, continuity_heavy_weight=False)

A method that searches for matches between the variables, but enables also “cross matches” after finding one match, i.e. after finding one of the longest match, every match between the remained letters will be legal.

#### Parameters: 

***min_len*** **(int, default 2):** Minimum length of letters that will be related as a match.

***continuity_heavy_weight*** **(boolean, default False):** the weight to let to continuity. False means relating to the "glue" between all the letters or words as one component, while True means relating each "glue" as one element. This "glue" means: for letting to match of some continuous elements heavy weight than the same number of single elements, we give a weight also to the "space" between letters, that will be received only when the elements of both sides of this space matches in one match. The weight of that is set by this variable.

#### Return value:

*MatchingBlocks* object.


### *NamesMatcher*.unedit_match(min_len=2, continuity_heavy_weight=False)

A method (that may be useful in curious cases) that after each match removes it from the variables, and concatenating both sides of it. (As a result, letters on the left side with those from right side of the match could build a new word).

#### Parameters: 

***min_len*** **(int, default 2):** Minimum length of letters that will be related as a match.

***continuity_heavy_weight*** **(boolean, default False):** the weight to let to continuity. False means relating to the "glue" between all the letters or words as one component, while True means relating each "glue" as one element. This "glue" means: for letting to match of some continuous elements heavy weight than the same number of single elements, we give a weight also to the "space" between letters, that will be received only when the elements of both sides of this space matches in one match. The weight of that is set by this variable.

#### Return value:

*MatchingBlocks* object.


### *NamesMatcher*.ordered_words_match(min_word_match_degree=2/3, prefer_num_of_letters=False, continuity_heavy_weight=False, ignore_stop_words=False)

A method that finds the matches that maximize the ratio between the variables words, while requires - after finding a match with maximal number of letters, the searching for other matches will be done separately on the left sides and the right sides of the match.

Note: this method uses dynamic programming for calculate that. As a result, the running time is about m^{2}n^{2}, while m and n are number of words in the first and second variables, respectively.

#### Parameters: 

***min_word_match_degree*** **(float, default 1):** Set the minimum ratio between two words to be intended as a match (1 means perfect match).

***prefer_num_of_letters*** **(bool, default False):** Set if to prefer - when searching after the “longest match”, if there are two continuity of words with the same ratio but one of them contains more words and another more letters if to take the match with more letters (True) or with more words (False).

***continuity_heavy_weight*** **(boolean, default False):** the weight to let to continuity. False means relating to the "glue" between all the letters or words as one component, while True means relating each "glue" as one element. This "glue" means: for letting to match of some continuous elements heavy weight than the same number of single elements, we give a weight also to the "space" between letters, that will be received only when the elements of both sides of this space matches in one match. The weight of that is set by this variable.

***ignore_stop_words*** **(bool, default False):** if to ignore Stop Words (as listed in the NamesMatcher object) in the names that has been compared.

#### Return value:

*MatchingBlocks* object.


### *NamesMatcher*.ordered_semantic_match(min_word_match_degree=2/3, prefer_num_of_letters=False, continuity_heavy_weight=False, ignore_stop_words=False)

A method that finds the matches that maximize the ratio between the variables words, while requires - after finding a match with maximal number of letters, the searching for other matches will be done separately on the left sides and the right sides of the match.

Note: this method uses dynamic programming for calculate that. As a result, the running time is about m^{2}n^{2}, while m and n are number of words in the first and second variables, respectively.

#### Parameters: 

***min_word_match_degree*** **(float, default 1):** Set the minimum ratio between two words to be intended as a match (1 means perfect match).

***prefer_num_of_letters*** **(bool, default False):** Set if to prefer - when searching after the “longest match”, if there are two continuity of words with the same ratio but one of them contains more words and another more letters if to take the match with more letters (True) or with more words (False).

***continuity_heavy_weight*** **(boolean, default False):** the weight to let to continuity. False means relating to the "glue" between all the letters or words as one component, while True means relating each "glue" as one element. This "glue" means: for letting to match of some continuous elements heavy weight than the same number of single elements, we give a weight also to the "space" between letters, that will be received only when the elements of both sides of this space matches in one match. The weight of that is set by this variable.

***ignore_stop_words*** **(bool, default False):** if to ignore Stop Words (as listed in the NamesMatcher object) in the names that has been compared.

#### Return value:

*MatchingBlocks* object.


### *NamesMatcher*.unordered_words_match(min_word_match_degree=2/3, prefer_num_of_letters=False continuity_heavy_weight=False, ignore_stop_words=False)

A method that searches for matches between the names in a variables, and enables also “cross matches” after finding one match, i.e. after finding one of the longest match, every match between the remained letters will be legal. In addition, it enables not perfect matching between words - depend on a parameter the user set.

#### Parameters: 

***min_word_match_degree*** **(float, default 1):** Set the minimum ratio between two words to be intended as a match (1 means perfect match).

***prefer_num_of_letters*** **(bool, default False):** Set if to prefer - when searching after the “longest match”, if there are two continuity of words with the same ratio but one of them contains more words and another more letters if to take the match with more letters (True) or with more words (False).

***continuity_heavy_weight*** **(boolean, default False):** the weight to let to continuity. False means relating to the "glue" between all the letters or words as one component, while True means relating each "glue" as one element. This "glue" means: for letting to match of some continuous elements heavy weight than the same number of single elements, we give a weight also to the "space" between letters, that will be received only when the elements of both sides of this space matches in one match. The weight of that is set by this variable.

***ignore_stop_words*** **(bool, default False):** if to ignore Stop Words (as listed in the NamesMatcher object) in the names that has been compared.

#### Return value:

*MatchingBlocks* object.


### *NamesMatcher*.unordered_semantic_match(min_word_match_degree=2/3, prefer_num_of_letters=False continuity_heavy_weight=False, ignore_stop_words=False)

A method that searches for matches between the names in a variables, and enables also “cross matches” after finding one match, i.e. after finding one of the longest match, every match between the remained letters will be legal. In addition, it enables not perfect matching between words - depend on a parameter the user set, and enable match between synonyms and singular/plural words.

#### Parameters: 

***min_word_match_degree*** **(float, default 1):** Set the minimum ratio between two words to be intended as a match (1 means perfect match).

***prefer_num_of_letters*** **(bool, default False):** Set if to prefer - when searching after the “longest match”, if there are two continuity of words with the same ratio but one of them contains more words and another more letters if to take the match with more letters (True) or with more words (False).

***continuity_heavy_weight*** **(boolean, default False):** the weight to let to continuity. False means relating to the "glue" between all the letters or words as one component, while True means relating each "glue" as one element. This "glue" means: for letting to match of some continuous elements heavy weight than the same number of single elements, we give a weight also to the "space" between letters, that will be received only when the elements of both sides of this space matches in one match. The weight of that is set by this variable.

***ignore_stop_words*** **(bool, default False):** if to ignore Stop Words (as listed in the NamesMatcher object) in the names that has been compared.

#### Return value:

*MatchingBlocks* object.
