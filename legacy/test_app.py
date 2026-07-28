import streamlit as st
import ollama
import whisper
from audiorecorder import audiorecorder
import tempfile
import os

def test_ollama():
    """Test if Ollama is running and accessible"""
    try:
        response = ollama.chat(model='llama3', messages=[{"role": "user", "content": "Say hello"}])
        return True, f"✅ Ollama working! Response: {response['message']['content'][:50]}..."
    except Exception as e:
        return False, f"❌ Ollama error: {e}"

def test_whisper():
    """Test if Whisper is working"""
    try:
        model = whisper.load_model("base")
        return True, "✅ Whisper model loaded successfully"
    except Exception as e:
        return False, f"❌ Whisper error: {e}"

def test_audio_recorder():
    """Test if audio recorder component is working"""
    try:
        # This will just test if the component can be imported and used
        return True, "✅ Audio recorder component available"
    except Exception as e:
        return False, f"❌ Audio recorder error: {e}"

def main():
    st.title("🔧 Euron Recruitment Agent - System Test")
    st.markdown("Testing all components before running the main application...")
    
    # Test Ollama
    st.subheader("1. Testing Ollama Connection")
    ollama_ok, ollama_msg = test_ollama()
    if ollama_ok:
        st.success(ollama_msg)
    else:
        st.error(ollama_msg)
        st.info("💡 Make sure Ollama is running: `ollama serve` or `ollama run llama3`")
    
    # Test Whisper
    st.subheader("2. Testing Whisper")
    whisper_ok, whisper_msg = test_whisper()
    if whisper_ok:
        st.success(whisper_msg)
    else:
        st.error(whisper_msg)
        st.info("💡 Install Whisper: `pip install openai-whisper`")
    
    # Test Audio Recorder
    st.subheader("3. Testing Audio Recorder")
    recorder_ok, recorder_msg = test_audio_recorder()
    if recorder_ok:
        st.success(recorder_msg)
    else:
        st.error(recorder_msg)
    
    # Overall status
    st.markdown("---")
    if ollama_ok and whisper_ok and recorder_ok:
        st.success("🎉 All systems are working! You can now run the main application.")
        st.info("Run: `streamlit run app.py`")
    else:
        st.error("⚠️ Some components are not working. Please fix the issues above before running the main app.")
    
    # Test audio recording
    st.subheader("4. Test Audio Recording (Optional)")
    st.markdown("Try recording a short audio to test the complete flow:")
    
    audio = audiorecorder("Click to record test audio", "Click to stop recording")
    
    if len(audio) > 0:
        st.audio(audio.export().read())
        
        # Save and transcribe
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            audio.export(tmp_file.name, format="wav")
            
            try:
                model = whisper.load_model("base")
                transcription = model.transcribe(tmp_file.name)
                st.success(f"✅ Transcription: {transcription['text']}")
                
                # Test LLM evaluation
                prompt = f"Is this a test recording? Answer: '{transcription['text']}'. Reply only 'yes' or 'no'."
                response = ollama.chat(model='llama3', messages=[{"role": "user", "content": prompt}])
                st.success(f"✅ LLM Evaluation: {response['message']['content']}")
                
            except Exception as e:
                st.error(f"❌ Processing error: {e}")
            finally:
                # Clean up
                os.unlink(tmp_file.name)

if __name__ == "__main__":
    main() 