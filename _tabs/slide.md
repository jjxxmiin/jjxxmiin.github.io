---
icon: fa-solid fa-tv
order: 3
---

---
icon: fa-solid fa-tv
order: 3
---

<style>
.slide-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 25px;
    padding: 20px 0;
}

.slide-card {
    background: #fff;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 4px 15px rgba(0,0,0,0.05);
    border: 1px solid #eee;
    display: flex;
    flex-direction: column;
    transition: all 0.3s ease;
}
.dark .slide-card {
    background: #1e1e1e;
    border-color: #333;
}

.slide-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 10px 25px rgba(0,0,0,0.1);
}

.slide-iframe-wrapper {
    position: relative;
    width: 100%;
    padding-top: 56.25%; /* 16:9 Aspect Ratio */
    background: #000;
}

.slide-iframe-wrapper iframe {
    position: absolute;
    top: 0;
    left: 0;
    bottom: 0;
    right: 0;
    width: 100%;
    height: 100%;
    border: none;
}

.slide-content {
    padding: 15px;
    display: flex;
    flex-direction: column;
    flex-grow: 1;
}

.slide-title {
    font-size: 1.1rem;
    font-weight: 700;
    margin-bottom: 15px;
    color: #333;
    line-height: 1.4;
}
.dark .slide-title { color: #eee; }

.slide-btn {
    margin-top: auto;
    display: inline-block;
    padding: 8px 16px;
    background: #f1f3f5;
    color: #333;
    text-align: center;
    border-radius: 6px;
    font-weight: 600;
    text-decoration: none;
    transition: background 0.2s;
}
.dark .slide-btn { background: #333; color: #fff; }
.slide-btn:hover { background: #e9ecef; text-decoration: none; }
.dark .slide-btn:hover { background: #444; }

.page-header {
    text-align: center;
    margin-bottom: 40px;
    padding-bottom: 20px;
    border-bottom: 1px solid #eee;
}
.dark .page-header { border-bottom-color: #333; }
.page-title { font-size: 2rem; font-weight: 800; margin-bottom: 10px; }
.page-desc { color: #666; }
</style>

<div class="page-header">
    <h1 class="page-title">Presentation Slides</h1>
    <p class="page-desc">Archive of my technical presentations and research slides.</p>
</div>

<div class="slide-grid">

    <!-- Simple Copy-Paste -->
    <div class="slide-card">
        <div class="slide-iframe-wrapper">
             <iframe src="//www.slideshare.net/slideshow/embed_code/key/MQrw7GtbBlPVQq" scrolling="no" allowfullscreen></iframe>
        </div>
        <div class="slide-content">
            <div class="slide-title">Simple Copy-Paste</div>
            <a href="https://jjeamin.github.io/assets/slide/2023-07-01-Simple_Copy_Paste.pptx" class="slide-btn"><i class="fa-solid fa-download"></i> Download</a>
        </div>
    </div>

    <!-- Rethinking Bisenet -->
    <div class="slide-card">
        <div class="slide-iframe-wrapper">
            <iframe src="//www.slideshare.net/slideshow/embed_code/key/33XhDfU3ncGu2A" scrolling="no" allowfullscreen></iframe>
        </div>
        <div class="slide-content">
            <div class="slide-title">Rethinking Bisenet</div>
            <a href="https://jjeamin.github.io/assets/slide/2022-01-17-Rethinking_Bisenet.pptx" class="slide-btn"><i class="fa-solid fa-download"></i> Download</a>
        </div>
    </div>

    <!-- Swin Transformer -->
    <div class="slide-card">
        <div class="slide-iframe-wrapper">
            <iframe src="//www.slideshare.net/slideshow/embed_code/key/kOypABCY8PhjCP" scrolling="no" allowfullscreen></iframe>
        </div>
        <div class="slide-content">
            <div class="slide-title">Swin Transformer</div>
            <a href="https://jjeamin.github.io/assets/slide/2021-06-03-SwinTransformer.pptx" class="slide-btn"><i class="fa-solid fa-download"></i> Download</a>
        </div>
    </div>

    <!-- TabNet -->
    <div class="slide-card">
        <div class="slide-iframe-wrapper">
            <iframe src="//www.slideshare.net/slideshow/embed_code/key/jixasnLuMgoTRh" scrolling="no" allowfullscreen></iframe>
        </div>
        <div class="slide-content">
            <div class="slide-title">TabNet</div>
            <a href="https://jjeamin.github.io/assets/slide/2021-06-02-Tabnet.pptx" class="slide-btn"><i class="fa-solid fa-download"></i> Download</a>
        </div>
    </div>

    <!-- U^2 Net -->
    <div class="slide-card">
        <div class="slide-iframe-wrapper">
            <iframe src="//www.slideshare.net/slideshow/embed_code/key/tEtjgtkeqt0dGV" scrolling="no" allowfullscreen></iframe>
        </div>
        <div class="slide-content">
            <div class="slide-title">U^2 Net</div>
            <a href="https://jjeamin.github.io/assets/slide/2021-05-04-U2-Net.pptx" class="slide-btn"><i class="fa-solid fa-download"></i> Download</a>
        </div>
    </div>

    <!-- Google NMT -->
    <div class="slide-card">
        <div class="slide-iframe-wrapper">
            <iframe src="//www.slideshare.net/slideshow/embed_code/key/1ToBfRGxbKP9XN" scrolling="no" allowfullscreen></iframe>
        </div>
        <div class="slide-content">
            <div class="slide-title">Google NMT</div>
            <a href="https://jjeamin.github.io/assets/slide/2021-04-04-GoogleNMT.pptx" class="slide-btn"><i class="fa-solid fa-download"></i> Download</a>
        </div>
    </div>

    <!-- SEAN -->
    <div class="slide-card">
        <div class="slide-iframe-wrapper">
            <iframe src="//www.slideshare.net/slideshow/embed_code/key/dTn5HPfrN4g3tQ" scrolling="no" allowfullscreen></iframe>
        </div>
        <div class="slide-content">
            <div class="slide-title">SEAN</div>
            <a href="https://jjeamin.github.io/assets/slide/2021-04-03-SEAN.pptx" class="slide-btn"><i class="fa-solid fa-download"></i> Download</a>
        </div>
    </div>
    
    <!-- DALL-E -->
    <div class="slide-card">
         <div class="slide-iframe-wrapper">
            <iframe src="//www.slideshare.net/slideshow/embed_code/key/CYOe0zvxwWta2G" scrolling="no" allowfullscreen></iframe>
        </div>
        <div class="slide-content">
            <div class="slide-title">Zero-Shot Text-to-Image Generation (DALL-E)</div>
            <a href="https://jjeamin.github.io/assets/slide/2021-04-01-DALLE.pptx" class="slide-btn"><i class="fa-solid fa-download"></i> Download</a>
        </div>
    </div>

    <!-- SPADE -->
    <div class="slide-card">
         <div class="slide-iframe-wrapper">
            <iframe src="//www.slideshare.net/slideshow/embed_code/key/pj1VvB1QyflIRr" scrolling="no" allowfullscreen></iframe>
        </div>
        <div class="slide-content">
            <div class="slide-title">Semantic Image Synthesis (SPADE)</div>
            <a href="https://jjeamin.github.io/assets/slide/2021-03-02-SPADE.pptx" class="slide-btn"><i class="fa-solid fa-download"></i> Download</a>
        </div>
    </div>

</div>
