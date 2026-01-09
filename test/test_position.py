
import sys
from http_sf import parse
from http_sf.errors import StructuredFieldError

def test_position():
    print("Testing Error Positioning...")
    
    # Test 1: Invalid character in List
    try:
        parse(b"foo, bar, \x00", tltype="list")
    except StructuredFieldError as e:
        assert e.position == 10, f"Expected position 10, got {e.position}"
        # offending_char for \x00
        assert e.offending_char == 0, f"Expected offending_char 0, got {e.offending_char}"
        print("  Test 1: OK")
    except Exception as e:
        print(f"  Test 1: FAIL (Wrong exception type: {type(e)})")
        raise

    # Test 2: Dictionary key context (failure in value)
    try:
        parse(b"key=1, key2=\x00", tltype="dictionary")
    except StructuredFieldError as e:
        assert e.position == 12, f"Expected position 12, got {e.position}" 
        # key2= is 5 chars. key=1, (6 chars) + space (1) = 7. 
        # key=1, key2=\x00
        # 0123456789012
        # k e y = 1 ,   k e y 2 = \x00
        # 0 1 2 3 4 5 6 7 8 9 0 1 2
        # Position 12 is correct.
        
        assert e.context == "key2", f"Expected context 'key2', got '{e.context}'"
        print("  Test 2: OK")
    except Exception as e:
        print(f"  Test 2: FAIL (Wrong exception type: {type(e)})")
        raise

    # Test 3: Trailing characters
    try:
        parse(b"123 trailing", tltype="item")
    except StructuredFieldError as e:
        assert e.position == 4, f"Expected position 4, got {e.position}"
        print("  Test 3: OK")
    except Exception as e:
        print(f"  Test 3: FAIL (Wrong exception type: {type(e)})")
        raise

    # Test 4: Parameter key context
    try:
        parse(b"item; param=\x00", tltype="item")
    except StructuredFieldError as e:
        assert e.position == 12, f"Expected position 12, got {e.position}"
        assert e.context == "param", f"Expected context 'param', got '{e.context}'"
        print("  Test 4: OK")
    except Exception as e:
        print(f"  Test 4: FAIL (Wrong exception type: {type(e)})")
        raise

    print("All Position Tests Passed.")

if __name__ == "__main__":
    test_position()
