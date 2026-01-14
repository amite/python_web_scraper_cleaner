
from mcp_server.news_server import _ask_news_logic

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

if __name__ == "__main__":
    verify()
