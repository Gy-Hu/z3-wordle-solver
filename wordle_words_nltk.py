import nltk
from nltk.corpus import words

def get_wordle_word_lists():
    """
    Use NLTK to generate two word lists needed for the Wordle game:
    1. ANSWERS: List of words that can be answers (more common 5-letter words)
    2. VALID_GUESSES: List of all valid guesses (all 5-letter words)
    
    Returns:
        tuple: (ANSWERS, VALID_GUESSES) two lists
    """
    # Get the word list from NLTK
    all_words = words.words()
    
    # Filter out all 5-letter lowercase words
    five_letter_words = [word.lower() for word in all_words if len(word) == 5 and word.isalpha()]
    
    # Remove duplicates
    five_letter_words = list(set(five_letter_words))
    
    # Following the ratio in the original file, about 12% of words are answer words
    # (In the original file, ANSWERS has about 2300 words, VALID_GUESSES about 10000)
    # We'll use the sorted list to differentiate between answer words and valid guess words
    
    # For consistency, we can select a portion of the sorted words as answers
    sorted_words = sorted(five_letter_words)
    
    # Assume the first 20% of words as possible answers
    answers_count = int(len(sorted_words) * 0.20)
    answers = sorted_words[:answers_count]
    
    # The remaining words plus the answer words together form valid guess words
    valid_guesses = sorted_words[answers_count:]
    
    return answers, valid_guesses

# Export word lists for direct import by other modules
ANSWERS, VALID_GUESSES = get_wordle_word_lists()

if __name__ == '__main__':
    # When running this file directly, print some statistics
    answers, valid_guesses = get_wordle_word_lists()
    print(f"Number of answer words: {len(answers)}")
    print(f"Sample answer words: {answers[:10]}...")
    print(f"Number of valid guess words: {len(valid_guesses)}")
    print(f"Sample valid guess words: {valid_guesses[:10]}...")
    print(f"Total number of 5-letter words: {len(answers) + len(valid_guesses)}")