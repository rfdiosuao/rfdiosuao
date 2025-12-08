import time
from clicker_core import HighResClicker

def test_clicker():
    print("Testing Clicker Core...")
    clicker = HighResClicker()
    
    # Test 1: Count Limit
    print("Test 1: 100 clicks at 50 CPS")
    clicker.cps = 50
    clicker.limit_mode = 'count'
    clicker.limit_value = 100
    
    start = time.time()
    clicker.start()
    clicker.thread.join() # Wait for it to finish
    end = time.time()
    
    duration = end - start
    print(f"Done. {clicker.total_clicks} clicks in {duration:.4f}s")
    print(f"Actual CPS: {clicker.total_clicks / duration:.2f}")
    
    if clicker.total_clicks == 100:
        print("PASS: Count limit working")
    else:
        print(f"FAIL: Expected 100 clicks, got {clicker.total_clicks}")

    # Test 2: High Speed (simulated)
    # Note: We can't easily verify actual clicks without a hook, 
    # but we can verify the loop speed.
    print("\nTest 2: High Speed Loop (500 CPS) for 2 seconds")
    clicker.cps = 500
    clicker.limit_mode = 'time'
    clicker.limit_value = 2.0
    
    start = time.time()
    clicker.start()
    clicker.thread.join()
    end = time.time()
    
    duration = end - start
    print(f"Done. {clicker.total_clicks} clicks in {duration:.4f}s")
    print(f"Actual CPS: {clicker.total_clicks / duration:.2f}")

if __name__ == "__main__":
    test_clicker()
