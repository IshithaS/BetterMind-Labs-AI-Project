import streamlit as st
import google.generativeai as genai
import logging
import PyPDF2
import io
import re
from PIL import Image, ImageDraw, ImageFont
import textwrap

api_key = "AIzaSyCFOndLMW6MI0EC-5ion89XACQgwk-dB1A"
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-1.5-flash")

st.set_page_config(page_title="AI-Driven Health Misinformation Detector", layout="centered")

st.markdown("""
    <style>
    .verdict {
        text-align: center;
        padding: 1rem;
        font-size: 2rem;
        font-weight: bold;
        border-radius: 0.5rem;
        margin-top: 2rem;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .right {
        color: #1a7f37;
        background-color: #e6ffed;
        border: 2px solid #1a7f37;
    }
    .wrong {
        color: #a20000;
        background-color: #ffe6e6;
        border: 2px solid #a20000;
    }
    .description {
        font-size: 1.3rem;
        font-weight: 700;
        margin-bottom: 1.5rem;
        color: #5a9bd4;
        font-family: 'Segoe UI Semibold', Verdana, Geneva, Tahoma, sans-serif;
        text-align: center;
    }
    .title {
        text-align: center;
        color: #5a9bd4;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="title">AI-Driven Health Misinformation Detector</h1>', unsafe_allow_html=True)
st.markdown('<p class="description">Analyze health-related text or PDFs to detect false claims and find trustworthy sources.</p>', unsafe_allow_html=True)

article_input = st.text_area("Enter any health-related article or snippet below.", height=200)
st.write("---")
uploaded_file = st.file_uploader("Or upload a PDF file for analysis", type="pdf")

content_to_analyze = ""
if uploaded_file:
    try:
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        for page in pdf_reader.pages:
            content_to_analyze += page.extract_text() + "\n"
        st.success("PDF uploaded and text extracted successfully!")
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
        logging.error(f"Error reading PDF: {e}")
elif article_input.strip():
    content_to_analyze = article_input

def extract_false_claims_and_explanations(text):
    blocks = re.findall(
        r"<span style='background-color: red; font-weight: bold;'>(.*?)</span>(.*?)?(?=<span style='background-color: red|YOU ARE RIGHT|YOU ARE WRONG|$)",
        text,
        re.DOTALL
    )
    return [(claim.strip(), explanation.strip()) for claim, explanation in blocks if claim.strip()]

def generate_poster_image(claims_explanations, reliable_sources=None):
    width, height = 1000, 1400
    img = Image.new("RGB", (width, height), "#fffefc")
    draw = ImageDraw.Draw(img)

    try:
        title_font = ImageFont.truetype("arialbd.ttf", 48)
        claim_font = ImageFont.truetype("arialbd.ttf", 30)
        explanation_font = ImageFont.truetype("arial.ttf", 24)
    except IOError:
        title_font = ImageFont.load_default()
        claim_font = ImageFont.load_default()
        explanation_font = ImageFont.load_default()

    y = 40
    title = "🚨 Detected Health Misinformation 🚨"
    w = draw.textlength(title, font=title_font)
    draw.text(((width - w) / 2, y), title, fill="red", font=title_font)
    y += 80
    draw.line([(50, y), (width - 50, y)], fill="red", width=4)
    y += 30


    def wrap_text(text, font, max_width):
        lines = []
        words = text.split()
        current_line = ""
        for word in words:
            test_line = current_line + " " + word if current_line else word
            if draw.textlength(test_line, font=font) <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        return lines

    max_text_width = width - 140 
    line_height_claim = 40
    line_height_expl = 32

    for claim, explanation in claims_explanations:
        box_top = y

        claim_lines = wrap_text(claim, claim_font, max_text_width)
        expl_lines = wrap_text(explanation, explanation_font, max_text_width)

        box_height = line_height_claim * len(claim_lines) + line_height_expl * len(expl_lines) + 40
        draw.rectangle([(50, box_top), (width - 50, box_top + box_height)], fill="#ffe6e6", outline="red", width=2)

        all_lines = claim_lines + expl_lines
        max_line_width = max(draw.textlength(f"❌ {line}" if i < len(claim_lines) else f"• {line}", 
                                            font=claim_font if i < len(claim_lines) else explanation_font)
                             for i, line in enumerate(all_lines))

        text_y = box_top + 15

        for i, line in enumerate(claim_lines):
            line_text = f"❌ {line}"
            line_w = draw.textlength(line_text, font=claim_font)
            x = 70 + (max_line_width - line_w) / 2
            draw.text((x, text_y), line_text, fill="darkred", font=claim_font)
            text_y += line_height_claim

        for i, line in enumerate(expl_lines):
            line_text = f"• {line}"
            line_w = draw.textlength(line_text, font=explanation_font)
            x = 70 + (max_line_width - line_w) / 2
            draw.text((x, text_y), line_text, fill="black", font=explanation_font)
            text_y += line_height_expl

        y = box_top + box_height + 20

    if reliable_sources:
        draw.text((50, y), "🔎 Trusted Sources:", fill="darkgreen", font=claim_font)
        y += 40
        for name, url in reliable_sources:
            lines = textwrap.wrap(f"{name} - {url}", width=80)
            for line in lines:
                line_w = draw.textlength(line, font=explanation_font)
                x = (width - line_w) / 2
                draw.text((x, y), line, fill="green", font=explanation_font)
                y += 30
            y += 10

    return img

if st.button("Analyze for Misinformation"):
    if not content_to_analyze.strip():
        st.warning("Please enter text or upload a PDF.")
    else:
        with st.spinner("Analyzing with Gemini..."):
            prompt = f"""
Analyze this health-related text for false claims:

\"\"\"{content_to_analyze}\"\"\"

Highlight false claims using <span style='background-color: red; font-weight: bold;'> tags. After each false claim, give a clear explanation. Use trusted source references like [CDC - https://cdc.gov]. End with 'YOU ARE RIGHT ✅' or 'YOU ARE WRONG ❌'.
"""
            try:
                response = model.generate_content(prompt)
                response.resolve()
                result_text = response.text.strip()
                st.session_state["misinfo_explanation"] = result_text

                if "YOU ARE RIGHT" in result_text:
                    st.markdown(result_text.replace("YOU ARE RIGHT", ""), unsafe_allow_html=True)
                    st.markdown("<div class='verdict right'>✅ YOU ARE RIGHT!</div>", unsafe_allow_html=True)
                elif "YOU ARE WRONG" in result_text:
                    st.markdown(result_text.replace("YOU ARE WRONG", ""), unsafe_allow_html=True)
                    st.markdown("<div class='verdict wrong'>❌ YOU ARE WRONG!</div>", unsafe_allow_html=True)
                else:
                    st.write(result_text)

                claims_expl = extract_false_claims_and_explanations(result_text)
                st.session_state["misinfo_claims"] = claims_expl

            except Exception as e:
                st.error(f"Gemini API error: {e}")

if "misinfo_claims" in st.session_state and st.session_state["misinfo_claims"]:
    st.markdown("### 🖼️ Generate Educational Poster")

    if st.button("Generate Poster Design", use_container_width=True):
        claims = st.session_state["misinfo_claims"]
        reliable_sources = [
            ("World Health Organization (WHO)", "https://www.who.int"),
            ("Centers for Disease Control and Prevention (CDC)", "https://www.cdc.gov"),
            ("Mayo Clinic", "https://www.mayoclinic.org")
        ]
        try:
            with st.spinner("Creating poster..."):
                poster_image = generate_poster_image(claims, reliable_sources)
                img_byte_arr = io.BytesIO()
                poster_image.save(img_byte_arr, format='PNG')
                img_byte_arr.seek(0)

                st.image(poster_image, caption="Generated Poster")
                st.download_button(
                    "Download Poster (PNG)",
                    data=img_byte_arr.getvalue(),
                    file_name="misinfo_poster.png",
                    mime="image/png"
                )
                st.success("Poster created!")
        except Exception as e:
            st.error(f"Poster generation failed: {e}")

if "misinfo_explanation" in st.session_state:
    st.markdown("### 🔍 Full AI Explanation")
    st.markdown(st.session_state["misinfo_explanation"], unsafe_allow_html=True)
