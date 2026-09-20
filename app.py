import json
import os
import tempfile
import google.generativeai as genai
from moviepy.editor import VideoFileClip
import streamlit as st
import whisper
import yt_dlp

st.set_page_config(
    page_title="AI Auto Clipper Video (YouTube)", layout="wide"
)
st.title("🎬 AI Auto Video Clipper - Edisi YouTube")

# Sidebar untuk Konfigurasi API
st.sidebar.header("Konfigurasi API")
api_key = st.sidebar.text_input(
    "Masukkan Gemini API Key (Gratis)", type="password"
)

youtube_url = st.text_input(
    "🔗 Masukkan Tautan Video YouTube (contoh: https://www.youtube.com/watch?v=...)"
)

if st.button("🚀 Unduh, Analisis & Potong"):
    if not api_key:
        st.error("Silakan masukkan Gemini API Key di sidebar sebelah kiri.")
        st.stop()
    if not youtube_url:
        st.error("Silakan masukkan tautan YouTube terlebih dahulu.")
        st.stop()

    genai.configure(api_key=api_key)

    # Menyiapkan tempat penyimpanan sementara di server
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
        video_path = tmp_file.name

    # Langkah 1: Unduh Video YouTube
    with st.spinner("⏳ 1/4 Mengunduh video dari YouTube (Resolusi 720p untuk stabilitas server)..."):
        try:
            # Mengunduh resolusi maksimal 720p agar server gratisan tidak kehabisan memori
            ydl_opts = {
                'format': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best',
                'outtmpl': video_path,
                'quiet': True,
                'merge_output_format': 'mp4'
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([youtube_url])
            st.success("Video berhasil diunduh ke server!")
        except Exception as e:
            st.error(f"Gagal mengunduh video. Pastikan tautan valid. Detail: {e}")
            st.stop()

    # Langkah 2: Transkripsi & Timestamp
    with st.spinner("🎙️ 2/4 Memproses audio dan ekstraksi teks menggunakan Whisper..."):
        model = whisper.load_model("base")
        result = model.transcribe(video_path)
        segments = [
            {"start": s["start"], "end": s["end"], "text": s["text"]}
            for s in result["segments"]
        ]

    # Langkah 3: Analisis Skor Viralitas dengan AI
    with st.spinner("🧠 3/4 Menganalisis poin viralitas dan hook menggunakan Gemini AI..."):
        prompt = f"""
        Analisis transkrip video berikut beserta timestamp (detik):
        {json.dumps(segments)}

        Tugasmu:
        1. Cari 2 hingga 3 bagian terbaik yang paling berpotensi viral (durasi tiap klip idealnya 30 - 60 detik).
        2. Berikan penilaian 'viral_score' (skala 1-100) berdasarkan ketajaman hook, emosi, atau informasi penting.
        3. Kembalikan hasil HANYA dalam format JSON array murni tanpa markdown formatting seperti berikut:
        [
            {{"start": 10.5, "end": 45.0, "score": 95, "reason": "Hook emosional kuat di awal pembicaraan"}},
            {{"start": 120.0, "end": 160.0, "score": 88, "reason": "Poin edukasi utama yang padat"}}
        ]
        """
        gemini_model = genai.GenerativeModel("gemini-1.5-flash")
        response = gemini_model.generate_content(prompt)

        raw_json = (
            response.text.strip()
            .replace("```json", "")
            .replace("```", "")
            .strip()
        )
        try:
            clips_data = json.loads(raw_json)
        except json.JSONDecodeError:
            st.error("AI gagal menghasilkan format data yang tepat. Silakan coba klik tombol proses sekali lagi.")
            st.stop()

    st.subheader("🔥 Hasil Deteksi Klip Berpotensi Viral")

    # Langkah 4: Pemotongan Video & Output 9:16
    for idx, clip in enumerate(clips_data):
        st.markdown(f"### Klip {idx+1} — Skor Viralitas: **{clip['score']}/100**")
        st.write(f"⏱️ **Durasi:** {clip['start']}s - {clip['end']}s | 💡 **Alasan:** {clip['reason']}")

        output_clip_path = f"viral_clip_{idx+1}.mp4"

        with st.spinner(f"✂️ 4/4 Memotong & mengubah format Klip {idx+1} ke 9:16..."):
            try:
                video_clip = VideoFileClip(video_path).subclip(clip["start"], clip["end"])

                # Center crop untuk rasio 9:16
                w, h = video_clip.size
                target_w = int(h * 9 / 16)
                crop_x1 = max(0, (w - target_w) // 2)

                final_clip = video_clip.crop(x1=crop_x1, y1=0, width=target_w, height=h)
                final_clip.write_videofile(
                    output_clip_path, codec="libx264", audio_codec="aac", logger=None
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
            except Exception as e:
                st.warning(f"Gagal memotong klip {idx+1}. Detail error: {e}")
