"""Basic agent query example."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.service import AsubarnipalService


def main():
    """Run basic query example."""
    print("=" * 60)
    print("Asubarnipal - Basic Query Example")
    print("=" * 60)

    service = AsubarnipalService()

    questions = [
        "What is machine learning?",
        "Explain the transformer architecture",
        "What are the main challenges in AI safety?",
    ]

    for question in questions:
        print(f"\n[Q] {question}")
        try:
            response = service.query(question)
            print(f"[A] {response[:300]}...")
        except Exception as e:
            print(f"[Error] {e}")

    print("\n" + "=" * 60)
    print("Done!")


if __name__ == "__main__":
    main()
