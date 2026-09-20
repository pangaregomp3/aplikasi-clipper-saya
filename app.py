import json
import os
import tempfile
import google.generativeai as genai
from moviepy.editor import VideoFileClip
import streamlit as st
import whisper

st.set_page_config(
    page_title="AI Auto Clipper Video (Gratis)", layout="wide"
)
st.title("🎬 AI Auto Video Clipper - Penganalisis Poin Viralitas")

# Sidebar untuk Konfigurasi API
st.sidebar.header("Konfigurasi API")
api_key = st.sidebar.text_input(
    "Masukkan Gemini API Key (Gratis)", type="password"
)

uploaded_file = st.file_uploader(
    "Unggah Video Durasi Panjang (MP4/MOV)", type=["mp4", "mov"]
)

if uploaded_file and api_key:
  genai.configure(api_key=api_key)

  # Simpan file sementara di server
  with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
    tmp_file.write(uploaded_file.read())
    video_path = tmp_file.name

  st.success("File video berhasil dimuat!")

  if st.button("🚀 Analisis & Potong Bagian Viral"):
    # Langkah 1: Transkripsi & Timestamp
    with st.spinner(
        "1/3 Memproses audio dan ekstraksi teks menggunakan Whisper..."
    ):
      model = whisper.load_model("base")
      result = model.transcribe(video_path)
      segments = [
          {"start": s["start"], "end": s["end"], "text": s["text"]}
          for s in result["segments"]
      ]

    # Langkah 2: Analisis Skor Viralitas dengan AI
    with st.spinner(
        "2/3 Menganalisis poin viralitas dan hook menggunakan Gemini AI..."
    ):
      prompt = f"""
            Analisis transkrip video berikut beserta timestamp (detik):
            {json.dumps(segments)}

            Tugasmu:
            1. Cari 2 hingga 4 bagian terbaik yang paling berpotensi viral (durasi tiap klip idealnya 30 - 60 detik).
            2. Berikan penilaian 'viral_score' (skala 1-100) berdasarkan ketajaman hook, emosi, atau informasi penting.
            3. Kembalikan hasil HANYA dalam format JSON array murni tanpa markdown formatting seperti berikut:
            [
              {{"start": 10.5, "end": 45.0, "score": 95, "reason": "Hook emosional kuat di awal pembicaraan"}},
              {{"start": 120.0, "end": 160.0, "score": 88, "reason": "Poin edukasi utama yang padat"}}
            ]
            """
      gemini_model = genai.GenerativeModel("gemini-1.5-flash")
      response = gemini_model.generate_content(prompt)

      # Cleaning response string untuk ekstraksi JSON
      raw_json = (
          response.text.strip()
          .replace("```json", "")
          .replace("```", "")
          .strip()
      )
      clips_data = json.loads(raw_json)

    st.subheader("🔥 Hasil Deteksi Klip Berpotensi Viral")

    # Langkah 3: Pemotongan Video & Output
    for idx, clip in enumerate(clips_data):
      st.markdown(
          f"### Klip {idx+1} — Skor Viralitas: **{clip['score']}/100**"
      )
      st.write(
          f"⏱️ **Durasi:** {clip['start']}s - {clip['end']}s | 💡 **Alasan:**"
          f" {clip['reason']}"
      )

      output_clip_path = f"viral_clip_{idx+1}.mp4"

      with st.spinner(f"Memotong & mengubah format Klip {idx+1} ke 9:16..."):
        video_clip = VideoFileClip(video_path).subclip(
            clip["start"], clip["end"]
        )

        # Pemotongan ke rasio vertikal 9:16 (Center Crop)
        w, h = video_clip.size
        target_w = int(h * 9 / 16)
        crop_x1 = max(0, (w - target_w) // 2)

        final_clip = video_clip.crop(x1=crop_x1, y1=0, width=target_w, height=h)
        final_clip.write_videofile(
            output_clip_path, codec="libx264", audio_codec="aac"
        )

      st.video(output_clip_path)

      with open(output_clip_path, "rb") as file:
        st.download_button(
            label=f"⬇️ Unduh Klip {idx+1}",
            data=file,
            file_name=f"viral_clip_{idx+1}.mp4",
            mime="video/mp4",
            key=f"dl_{idx}",
        )