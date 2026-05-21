"""H-Mem memory system demonstration."""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.service import HMemService


def main():
    """Run H-Mem demonstration."""
    print("=" * 60)
    print("Asubarnipal - H-Mem Memory System Demo")
    print("=" * 60)

    hmem = HMemService()

    # Add memories
    memories_to_add = [
        ("Python is a versatile programming language used in AI/ML", {"category": "tech", "importance": "high"}),
        ("The transformer architecture revolutionized NLP", {"category": "ai", "importance": "high"}),
        ("FAISS is a library for efficient similarity search", {"category": "tech", "importance": "medium"}),
        ("RAG combines retrieval with generation for better answers", {"category": "ai", "importance": "high"}),
    ]

    print("\n[1] Adding memories...")
    for text, metadata in memories_to_add:
        hmem.remember(text, metadata=metadata)
        print(f"  + Added: {text[:50]}...")

    # Show stats
    print("\n[2] Memory Statistics:")
    stats = hmem.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # Recall memories
    print("\n[3] Recalling memories about 'AI':")
    results = hmem.recall("artificial intelligence")
    for i, mem in enumerate(results, 1):
        print(f"  {i}. {mem.get('text', 'N/A')[:80]}...")

    # Think (query with answer)
    print("\n[4] Thinking about 'retrieval augmented generation':")
    try:
        answer = hmem.think("What do I know about RAG?")
        print(f"  Answer: {answer[:200]}...")
    except Exception as e:
        print(f"  [Error] {e}")

    # Get context
    print("\n[5] Getting context for 'programming':")
    context = hmem.get_context("programming")
    print(f"  Context: {context[:200]}...")

    print("\n" + "=" * 60)
    print("Demo complete!")


if __name__ == "__main__":
    main()
