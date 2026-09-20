import json
import os
import google.generativeai as genai
from moviepy.editor import VideoFileClip
import streamlit as st
import whisper
import yt_dlp

st.set_page_config(page_title="AI Auto Clipper Video (YouTube)", layout="wide")
st.title("🎬 AI Auto Video Clipper - Edisi YouTube")

st.sidebar.header("Konfigurasi API")
api_key = st.sidebar.text_input("Masukkan Gemini API Key (Gratis)", type="password")
youtube_url = st.text_input("🔗 Masukkan Tautan Video YouTube")

if st.button("🚀 Unduh, Analisis & Potong"):
    if not api_key:
        st.error("Silakan masukkan Gemini API Key di sidebar sebelah kiri.")
        st.stop()
    if not youtube_url:
        st.error("Silakan masukkan tautan YouTube.")
        st.stop()

    genai.configure(api_key=api_key)
    video_path = "temp_video.mp4"

    if os.path.exists(video_path):
        os.remove(video_path)

    # Langkah 1: Unduh File (Dengan trik penyamaran Android)
    with st.spinner("⏳ 1/4 Mengunduh video (Menyamar sebagai perangkat seluler)..."):
        try:
            ydl_opts = {
                'format': 'best[height<=480]/bestvideo[height<=480]+bestaudio/best',
                'outtmpl': video_path,
                'merge_output_format': 'mp4',
                'quiet': True,
                'nocheckcertificate': True,
                # Trik khusus: Menyamar sebagai aplikasi Android agar tidak diblokir YouTube (403)
                'extractor_args': {'youtube': ['player_client=android']}
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([youtube_url])
            
            if not os.path.exists(video_path) or os.path.getsize(video_path) == 0:
                st.error("File kosong. YouTube mungkin memblokir akses ke video ini secara ketat.")
                st.stop()
                
            st.success("Video berhasil diunduh dengan aman!")
        except Exception as e:
            st.error(f"Gagal mengunduh video. Detail: {e}")
            st.stop()

    # Langkah 2: Proses Suara (Whisper)
    with st.spinner("🎙️ 2/4 Membaca suara menggunakan AI Whisper..."):
        try:
            model = whisper.load_model("base")
            result = model.transcribe(video_path)
            segments = [{"start": s["start"], "end": s["end"], "text": s["text"]} for s in result["segments"]]
        except Exception as e:
            st.error(f"Gagal membaca audio video. Detail Error: {e}")
            st.stop()

    # Langkah 3: Analisis AI Gemini
    with st.spinner("🧠 3/4 Menganalisis poin viralitas dengan AI Gemini..."):
        prompt = f"""
        Analisis transkrip video berikut beserta timestamp (detik):
        {json.dumps(segments)}

        Tugasmu:
        1. Cari 2 hingga 3 bagian terbaik yang berpotensi viral (durasi 30-60 detik).
        2. Berikan penilaian 'viral_score' (1-100).
        3. Kembalikan hasil HANYA format JSON murni tanpa awalan/akhiran apapun:
        [
          {{"start": 10.5, "end": 45.0, "score": 95, "reason": "Hook emosional kuat"}},
          {{"start": 120.0, "end": 160.0, "score": 88, "reason": "Poin edukasi padat"}}
        ]
        """
        try:
            gemini_model = genai.GenerativeModel("gemini-1.5-flash")
            response = gemini_model.generate_content(prompt)
            raw_json = response.text.strip().replace("```json", "").replace("```", "").strip()
            clips_data = json.loads(raw_json)
        except Exception as e:
            st.error("AI Gemini gagal memproses format. Silakan klik tombol kembali.")
            st.stop()

    st.subheader("🔥 Hasil Deteksi Klip")

    # Langkah 4: Pemotongan Video Vertikal
    for idx, clip in enumerate(clips_data):
        st.markdown(f"### Klip {idx+1} — Skor: **{clip['score']}/100**")
        st.write(f"⏱️ **Durasi:** {clip['start']}s - {clip['end']}s | 💡 **Alasan:** {clip['reason']}")
        output_clip_path = f"viral_clip_{idx+1}.mp4"

        with st.spinner(f"✂️ 4/4 Memotong Klip {idx+1} ke rasio 9:16 (TikTok/Reels)..."):
            try:
                video_clip = VideoFileClip(video_path).subclip(clip["start"], clip["end"])
                
                w, h = video_clip.size
                target_w = int(h * 9 / 16)
                crop_x1 = max(0, (w - target_w) // 2)

                final_clip = video_clip.crop(x1=crop_x1, y1=0, width=target_w, height=h)
                final_clip.write_videofile(output_clip_path, codec="libx264", audio_codec="aac", logger=None)
                
                st.video(output_clip_path)
                with open(output_clip_path, "rb") as file:
                    st.download_button(
                        label=f"⬇️ Unduh Klip {idx+1}", data=file, file_name=f"viral_clip_{idx+1}.mp4", mime="video/mp4", key=f"dl_{idx}"
                    )
            except Exception as e:
                st.warning(f"Gagal memotong klip {idx+1}. Detail: {e}")
