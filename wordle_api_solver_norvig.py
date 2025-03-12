import copy
import json
import logging
import requests
import time
from wordle_words import ANSWERS, VALID_GUESSES
import z3

# Configure logging
logging.basicConfig(
    handlers=[
        logging.FileHandler("wordle_api_output.log", mode='w'),
        logging.StreamHandler()
    ]
)
logging.getLogger().setLevel(logging.INFO)

# Constants
ANSWER_LEN = 5  # The size of the word, 5 means 5 character word
ALPHABET_RANGE = False  # Flag to determine should we add an explicit range for each "letter" from 0-25
VALID_GUESS_COUNT = 10  # The number of valid guesses z3 gets before we give up
IS_OPTIMIZE = True  # Whether we should use the z3.Solver() or z3.Optimize()
API_URL = "https://wordle.votee.dev:8000/daily"  # The API URL for the Wordle game

# Preference flags
PREFER_NO_DUPLICATE_CHARS = True  # Only use duplicate characters in words when we have to
PREFER_2_OR_LESS_DUPLICATE_CHARS = True  # Don't use MORE than two of the same character in words until we have to

# Strategy 22: Norvig's strategy - use these four words first
NORVIG_GUESSES = ["handy", "swift", "glove", "crump"]

COMMON_WORDS = ANSWERS + VALID_GUESSES

class Result:
    """Result object for one answer simulation"""
    def __init__(self, guesses, time_to_solve):
        self.guesses = guesses
        self.time_to_solve = time_to_solve

    def __str__(self):
        """String representation of the result"""
        return f"Guesses: {', '.join(self.guesses)}, Count: {len(self.guesses)}, Time: {self.time_to_solve}s"


def get_current_model_word(letters, model, alphabet):
    """
    Get the current string representation of the model
    """
    return ''.join([alphabet[model[letter_key].as_long()] for letter_key in letters])


def make_guess(word):
    """
    Make a guess to the Wordle API and get the result
    """
    try:
        response = requests.get(f"{API_URL}?guess={word}")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error(f"Error making guess: {e}")
        return None


def process_guess_result(guess, guess_result):
    """
    Process the result of a guess and return constraints for the solver
    """
    # Set of characters from the guess not in the answer at all
    guess_character_not_in_answer = set()
    # A list of (character index, character) tuples from the guess in the correct position for the answer
    guess_character_in_answer_right_position = []
    # A list of (character index, character) tuples from the guess in the word but not in the correct position
    guess_character_in_answer_wrong_position = []
    # A set of (character index, character, at most count) tuples for limiting character occurrences
    guess_character_in_answer_at_most = set()
    
    # Create a frequency map for characters in the guess
    guess_char_freq = {}
    for c in guess:
        if c in guess_char_freq:
            guess_char_freq[c] += 1
        else:
            guess_char_freq[c] = 1
    
    # Create a frequency map for "present" and "correct" characters
    present_correct_freq = {}
    
    # First pass: identify correct and present characters
    for item in guess_result:
        slot = item["slot"]
        char = item["guess"]
        result = item["result"]
        
        if result == "correct":
            guess_character_in_answer_right_position.append((slot, char))
            if char in present_correct_freq:
                present_correct_freq[char] += 1
            else:
                present_correct_freq[char] = 1
        elif result == "present":
            guess_character_in_answer_wrong_position.append((slot, char))
            if char in present_correct_freq:
                present_correct_freq[char] += 1
            else:
                present_correct_freq[char] = 1
        elif result == "absent":
            # We'll handle absent characters in the second pass
            pass
    
    # Second pass: handle absent characters
    for item in guess_result:
        slot = item["slot"]
        char = item["guess"]
        result = item["result"]
        
        if result == "absent":
            # If the character appears elsewhere as present/correct but not here,
            # it means there are exactly present_correct_freq[char] occurrences
            if char in present_correct_freq:
                # This character is limited to present_correct_freq[char] occurrences
                if guess_char_freq[char] > present_correct_freq[char]:
                    guess_character_in_answer_at_most.add((slot, char, present_correct_freq[char]))
            else:
                # The character is not in the answer at all
                guess_character_not_in_answer.add(char)
    
    return (
        guess_character_not_in_answer,
        guess_character_in_answer_right_position,
        guess_character_in_answer_wrong_position,
        guess_character_in_answer_at_most
    )


def solve_wordle_api_norvig():
    """
    Solve the Wordle puzzle using the API with Strategy 22 (Norvig's strategy)
    """
    start_time = time.time()
    
    # Our alphabet
    alphabet = 'abcdefghijklmnopqrstuvwxyz'
    # Represents each letter in the word as an integer
    letters = [z3.Int(f"letter_{i}") for i in range(ANSWER_LEN)]
    
    # Create the solver
    solver = z3.Optimize() if IS_OPTIMIZE else z3.Solver()
    
    # Add alphabet range constraints if needed
    if ALPHABET_RANGE:
        logging.info("Using alphabet range")
        for letter in letters:
            solver.add(letter >= 0, letter <= 25)
    
    # Build a disjunction of all words the solver can guess
    all_words_disjunction = []
    for word in COMMON_WORDS:
        if len(word) == ANSWER_LEN:
            word_conjunction = z3.And([letters[i] == ord(word[i]) - 97 for i in range(len(word))])
            all_words_disjunction.append(word_conjunction)
    
    # Add the all_words_disjunction to the solver
    solver.add(z3.Or(all_words_disjunction))
    
    # Add preference constraints
    if IS_OPTIMIZE:
        if PREFER_NO_DUPLICATE_CHARS:
            # Prefer non-duplicate letters
            solver.add_soft(z3.Distinct(tuple([letter for letter in letters])), 100)
        if PREFER_2_OR_LESS_DUPLICATE_CHARS:
            for c in alphabet:
                two_or_less_cc = [letter == ord(c) - 97 for letter in letters]
                two_or_less_cc.append(2)
                solver.add_soft(z3.AtMost(tuple(two_or_less_cc)), 100)
    
    # Keep track of guesses
    guessed = []
    
    # Strategy 22: Use Norvig's strategy of fixed guesses first
    logging.info("Using Strategy 22: Norvig's strategy")
    
    # Make the Norvig guesses first
    for norvig_guess in NORVIG_GUESSES:
        logging.info(f"Making Norvig guess: {norvig_guess}")
        
        # Make the guess
        guess_result = make_guess(norvig_guess)
        if not guess_result:
            logging.error(f"Failed to get result for guess: {norvig_guess}")
            return None
        
        guessed.append(norvig_guess)
        logging.info(f"Guess result: {guess_result}")
        
        # Check if we won
        if all(item["result"] == "correct" for item in guess_result):
            logging.info(f"WINNER! {len(guessed)}")
            return Result(guessed, round(time.time() - start_time, 2))
        
        # Process the guess result
        (
            guess_character_not_in_answer,
            guess_character_in_answer_right_position,
            guess_character_in_answer_wrong_position,
            guess_character_in_answer_at_most
        ) = process_guess_result(norvig_guess, guess_result)
        
        # Add constraints from the guess
        # Add constraints for guess characters in the same position as answer
        for i, c in guess_character_in_answer_right_position:
            solver.add(letters[i] == ord(c) - 97)
        
        # Add constraints for guess characters not in the correct position for answer
        for i, c in guess_character_in_answer_wrong_position:
            # Add constraint that it's impossible for the character to exist in this letter position
            solver.add(letters[i] != ord(c) - 97)
            # If this character is in the word but not in this position, then it must be in one of the other positions
            solver.add(z3.Or([letters[j] == ord(c) - 97 for j in range(len(letters)) if j != i]))
        
        # Add constraints for guess characters not in the answer at all
        for c in guess_character_not_in_answer:
            # Iterate each letter representation the answer
            for letter in letters:
                # Add constraint that it's impossible for the character to exist in this letter position
                solver.add(letter != ord(c) - 97)
        
        # Add constraints for guess characters that should appear no more than "X" times in answer
        letters_processed = set()
        for i, c, f in guess_character_in_answer_at_most:
            # Add constraint that it's impossible for the character to exist in this letter position
            solver.add(letters[i] != ord(c) - 97)
            # If we haven't added our cardinality constraint for this character, do it now
            if c not in letters_processed:
                # Build a tuple that essentially says:
                #   For all the letters in letter, character <current character> should appear AT MOST f times
                at_most_cc = [letter == ord(c) - 97 for letter in letters]
                at_most_cc.append(f)
                # Cardinality constraint
                solver.add(z3.AtMost(tuple(at_most_cc)))
                letters_processed.add(c)
    
    # After Norvig's guesses, use Z3 for the remaining guesses (5 and 6)
    logging.info("Norvig's guesses complete, using Z3 for remaining guesses")
    
    # Continue guessing until we find the answer or reach the limit
    while len(guessed) < VALID_GUESS_COUNT:
        # Check if the constraints are satisfiable
        check_sat = solver.check()
        if check_sat != z3.sat:
            logging.error("No solution found - constraints are unsatisfiable")
            break
        
        # Get the next guess
        model = solver.model()
        guess = get_current_model_word(letters, model, alphabet)
        
        logging.info(f"Z3 guess: {guess}")
        guessed.append(guess)
        
        # Make the guess
        guess_result = make_guess(guess)
        if not guess_result:
            logging.error(f"Failed to get result for guess: {guess}")
            break
        
        logging.info(f"Guess result: {guess_result}")
        
        # Check if we won
        if all(item["result"] == "correct" for item in guess_result):
            logging.info(f"WINNER! {len(guessed)}")
            break
        
        # Process the guess result
        (
            guess_character_not_in_answer,
            guess_character_in_answer_right_position,
            guess_character_in_answer_wrong_position,
            guess_character_in_answer_at_most
        ) = process_guess_result(guess, guess_result)
        
        # Add constraints from the guess
        # Add constraints for guess characters in the same position as answer
        for i, c in guess_character_in_answer_right_position:
            solver.add(letters[i] == ord(c) - 97)
        
        # Add constraints for guess characters not in the correct position for answer
        for i, c in guess_character_in_answer_wrong_position:
            # Add constraint that it's impossible for the character to exist in this letter position
            solver.add(letters[i] != ord(c) - 97)
            # If this character is in the word but not in this position, then it must be in one of the other positions
            solver.add(z3.Or([letters[j] == ord(c) - 97 for j in range(len(letters)) if j != i]))
        
        # Add constraints for guess characters not in the answer at all
        for c in guess_character_not_in_answer:
            # Iterate each letter representation the answer
            for letter in letters:
                # Add constraint that it's impossible for the character to exist in this letter position
                solver.add(letter != ord(c) - 97)
        
        # Add constraints for guess characters that should appear no more than "X" times in answer
        letters_processed = set()
        for i, c, f in guess_character_in_answer_at_most:
            # Add constraint that it's impossible for the character to exist in this letter position
            solver.add(letters[i] != ord(c) - 97)
            # If we haven't added our cardinality constraint for this character, do it now
            if c not in letters_processed:
                # Build a tuple that essentially says:
                #   For all the letters in letter, character <current character> should appear AT MOST f times
                at_most_cc = [letter == ord(c) - 97 for letter in letters]
                at_most_cc.append(f)
                # Cardinality constraint
                solver.add(z3.AtMost(tuple(at_most_cc)))
                letters_processed.add(c)
    
    # Calculate time to solve
    tts = round(time.time() - start_time, 2)
    return Result(guessed, tts)


if __name__ == '__main__':
    logging.info("Starting Wordle API Solver with Norvig's Strategy (Strategy 22)")
    result = solve_wordle_api_norvig()
    if result:
        logging.info(f"Result: {result}")
    else:
        logging.error("Failed to solve the puzzle")
