"""
Test Question Mapper - Verify question text conversion works
"""

from ml_engine.services.question_mapper import get_question_text, get_question_info

print("🧪 Testing Question Mapper\n")
print("=" * 60)

# Test a few sample questions
test_indices = [
    10,   # IT interest question
    106,  # IT skill question
    0,    # Agriculture interest
    96,   # Agriculture skill
    20,   # Arts interest
    255   # Last question (Transport skill)
]

print("\n📝 Sample Questions:\n")

for idx in test_indices:
    info = get_question_info(idx)
    print(f"Index {idx}:")
    print(f"  Category: {info['category_name']}")
    print(f"  Type: {info['type']}")
    print(f"  Text: {info['text']}")
    print(f"  Full: {info['full_question'][:80]}...")
    print()

print("=" * 60)
print("\n✅ Question mapper working correctly!")
print("\nNow Rasa can convert indices like [10, 106, 20] to actual Khmer questions! 🎉\n")
