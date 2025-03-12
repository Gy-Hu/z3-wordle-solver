import nltk
from nltk.corpus import words
import requests
import logging
import json

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

# API URLs for different game modes
API_URLS = {
    "daily": "https://wordle.votee.dev:8000/daily",
    "random": "https://wordle.votee.dev:8000/random",
    "word": "https://wordle.votee.dev:8000/word"
}

def make_guess_daily(word, size=5):
    """
    Make a guess to the Wordle API in daily mode
    
    Args:
        word (str): The word to guess
        size (int, optional): The size of the word. Defaults to 5.
        
    Returns:
        list: The result of the guess, or None if there was an error
    """
    try:
        response = requests.get(f"{API_URLS['daily']}?guess={word}&size={size}")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error(f"Error making daily guess: {e}")
        return None

def make_guess_random(word, size=5, seed=None):
    """
    Make a guess to the Wordle API in random mode
    
    Args:
        word (str): The word to guess
        size (int, optional): The size of the word. Defaults to 5.
        seed (int, optional): Random seed for reproducible results. Defaults to None.
        
    Returns:
        list: The result of the guess, or None if there was an error
    """
    try:
        url = f"{API_URLS['random']}?guess={word}&size={size}"
        if seed is not None:
            url += f"&seed={seed}"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error(f"Error making random guess: {e}")
        return None

def make_guess_word(target_word, guess_word):
    """
    Make a guess to the Wordle API in word mode (guess against a specific word)
    
    Args:
        target_word (str): The target word to guess against
        guess_word (str): The word to guess
        
    Returns:
        list: The result of the guess, or None if there was an error
    """
    try:
        response = requests.get(f"{API_URLS['word']}/{target_word}?guess={guess_word}")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error(f"Error making word guess: {e}")
        return None

def make_guess(word, mode="daily", **kwargs):
    """
    Make a guess to the Wordle API in the specified mode
    
    Args:
        word (str): The word to guess
        mode (str, optional): The game mode ("daily", "random", or "word"). Defaults to "daily".
        **kwargs: Additional arguments for the specific mode:
            - For "daily" mode: size (int, optional)
            - For "random" mode: size (int, optional), seed (int, optional)
            - For "word" mode: target_word (str, required)
            
    Returns:
        list: The result of the guess, or None if there was an error
    """
    if mode == "daily":
        size = kwargs.get("size", 5)
        return make_guess_daily(word, size)
    elif mode == "random":
        size = kwargs.get("size", 5)
        seed = kwargs.get("seed", None)
        return make_guess_random(word, size, seed)
    elif mode == "word":
        target_word = kwargs.get("target_word")
        if not target_word:
            logging.error("Target word is required for word mode")
            return None
        return make_guess_word(target_word, word)
    else:
        logging.error(f"Unknown mode: {mode}")
        return None

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