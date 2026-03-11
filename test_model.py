import joblib
import numpy as np
import os

# Update this with your actual model filename
MODEL_PATH = 'model/shot_classifier.pkl'

def test_load():
    if not os.path.exists(MODEL_PATH):
        print(f"❌ Error: {MODEL_PATH} not found!")
        return

    try:
        # This is where the MT19937 crash usually happens
        model = joblib.load(MODEL_PATH)
        print("✅ Success: Model loaded without NumPy version errors!")
        
        # Test a dummy prediction (assuming your model expects MediaPipe landmarks)
        # Adjust the '132' if your input feature length is different
        dummy_input = np.random.rand(1, 132) 
        prediction = model.predict(dummy_input)
        print(f"✅ Success: Dummy prediction worked! Result: {prediction}")
        
    except Exception as e:
        print(f"❌ Crash detected: {e}")

if __name__ == "__main__":
    test_load()