
from news_server import _ask_news_logic

def reproduce():
    question = "What are danish officials saying?"
    print(f"Asking: {question}")
    answer = _ask_news_logic(question)
    print("\nAnswer:")
    print(answer)

if __name__ == "__main__":
    reproduce()
