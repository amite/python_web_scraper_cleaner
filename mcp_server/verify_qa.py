
from news_server import _ask_news_logic
import sys

def verify():
    question = "What is the latest news from Iran?"
    print(f"Asking: {question}")
    answer = _ask_news_logic(question)
    print("\nAnswer:")
    print(answer)
    
    if "Iran" in answer or "protest" in answer or "crackdown" in answer:
        print("\nSUCCESS: Answer seems relevant.")
    elif "couldn't find any relevant" in answer:
        print("\nFAILURE: No article found.")
    else:
        print("\nWARNING: Answer might not be relevant.")
        
    # Test a query that should fail
    print("\nAsking nonsense...")
    answer_fail = _ask_news_logic("asdfghjkl")
    if "couldn't find" in answer_fail:
        print("SUCCESS: Correctly handled missing info.")
    else:
        print("WARNING: Should have failed.")

if __name__ == "__main__":
    verify()
