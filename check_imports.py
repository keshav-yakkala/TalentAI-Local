try:
    import streamlit as st
    import pandas as pd
    import matplotlib.pyplot as plt
    from audiorecorder import audiorecorder
    import numpy as np
    import ollama
    import whisper
    import PyPDF2
    from pydub import AudioSegment
    print("All imports successful!")
except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"Error: {e}")
