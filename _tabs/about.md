---
# the default layout is 'page'
icon: fa-regular fa-user
order: 1
---

<style>
/* Modern Reset & Base */
.profile-container {
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif;
    color: #333;
    line-height: 1.6;
    max-width: 900px;
    margin: 0 auto;
    padding: 20px 0;
}
.dark .profile-container { color: #e0e0e0; }

/* Hero Section */
.hero-section {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    margin-bottom: 60px;
    padding: 40px 20px;
    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    border-radius: 24px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.05);
}
.dark .hero-section {
    background: linear-gradient(135deg, #2d3436 0%, #000000 100%);
    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
}

.hero-name {
    font-size: 2.5rem;
    font-weight: 800;
    margin: 15px 0 5px;
    background: linear-gradient(90deg, #007cf0, #00dfd8);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.hero-subtitle {
    font-size: 1.1rem;
    color: #666;
    font-weight: 500;
}
.dark .hero-subtitle { color: #aaa; }

.contact-btn {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    margin-top: 20px;
    padding: 10px 24px;
    background: #000;
    color: #fff;
    border-radius: 50px;
    text-decoration: none;
    font-weight: 600;
    transition: transform 0.2s, box-shadow 0.2s;
}
.dark .contact-btn { background: #fff; color: #000; }
.contact-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 5px 15px rgba(0,0,0,0.2);
    text-decoration: none;
    color: inherit;
}

/* Social Links */
.social-links {
    display: flex;
    gap: 15px;
    margin-top: 25px;
    flex-wrap: wrap;
    justify-content: center;
}
.social-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 16px;
    background: rgba(255,255,255,0.7);
    border: 1px solid rgba(0,0,0,0.05);
    border-radius: 12px;
    font-size: 0.9rem;
    color: #444;
    text-decoration: none;
    transition: all 0.2s;
    backdrop-filter: blur(5px);
}
.dark .social-item {
    background: rgba(255,255,255,0.05);
    border-color: rgba(255,255,255,0.1);
    color: #ccc;
}
.social-item:hover {
    background: #fff;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    text-decoration: none;
    color: #007cf0;
}
.dark .social-item:hover { color: #fff; background: rgba(255,255,255,0.1); }

/* Section Styles */
.section-title {
    font-size: 1.8rem;
    font-weight: 700;
    margin: 60px 0 30px;
    padding-bottom: 15px;
    border-bottom: 2px solid #eee;
    position: relative;
}
.dark .section-title { border-bottom-color: #333; }
.section-title::after {
    content: '';
    position: absolute;
    bottom: -2px;
    left: 0;
    width: 60px;
    height: 2px;
    background: #007cf0;
}

/* Grid Layouts */
.grid-container {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 20px;
}

.interest-card {
    padding: 20px;
    background: #fff;
    border-radius: 16px;
    border: 1px solid #eee;
    transition: all 0.3s ease;
}
.dark .interest-card { background: #1a1a1a; border-color: #333; }
.interest-card:hover { border-color: #007cf0; transform: translateY(-3px); }
.interest-icon { font-size: 1.5rem; color: #007cf0; margin-bottom: 10px; }
.interest-title { font-weight: 700; font-size: 1.1rem; margin-bottom: 5px; }

/* Timeline for Experience */
.timeline { position: relative; padding-left: 20px; border-left: 2px solid #eee; }
.dark .timeline { border-left-color: #333; }
.timeline-item { margin-bottom: 40px; position: relative; }
.timeline-item::before {
    content: '';
    position: absolute;
    left: -27px;
    top: 5px;
    width: 12px;
    height: 12px;
    background: #007cf0;
    border-radius: 50%;
    border: 3px solid #fff;
    box-shadow: 0 0 0 1px #eee;
}
.dark .timeline-item::before { background: #00dfd8; border-color: #1a1a1a; box-shadow: 0 0 0 1px #333; }

.timeline-date {
    font-size: 0.85rem;
    color: #888;
    font-weight: 600;
    margin-bottom: 5px;
    text-transform: uppercase;
    letter-spacing: 1px;
}
.timeline-company { font-size: 1.3rem; font-weight: 700; margin-bottom: 5px; }
.timeline-company a { color: inherit; text-decoration: none; border-bottom: 1px dashed #ccc; }
.timeline-role { font-size: 1rem; font-weight: 500; color: #555; margin-bottom: 10px; font-style: italic; }
.dark .timeline-role { color: #bbb; }
.timeline-desc { font-size: 0.95rem; color: #666; }
.dark .timeline-desc { color: #999; }

/* Publications */
.pub-item {
    margin-bottom: 25px;
    padding: 20px;
    border-radius: 12px;
    background: #f8f9fa;
    border-left: 4px solid #007cf0;
}
.dark .pub-item { background: #222; }
.pub-title { font-weight: 700; font-size: 1.05rem; margin-bottom: 8px; line-height: 1.4; }
.pub-authors { font-size: 0.9rem; color: #555; margin-bottom: 5px; }
.dark .pub-authors { color: #aaa; }
.pub-venue { font-size: 0.85rem; color: #007cf0; font-weight: 600; }
.pub-me { font-weight: 800; color: #000; }
.dark .pub-me { color: #fff; }

</style>

<div class="profile-container">

    <!-- Hero -->
    <div class="hero-section">
        <!-- Avatar can go here if provided, otherwise simple icon -->
        <i class="fa-solid fa-circle-user" style="font-size: 80px; color: #ddd; margin-bottom: 20px;"></i>
        <h1 class="hero-name">Jaemin Jeong</h1>
        <p class="hero-subtitle">Visual AI Researcher & Deep Learning Engineer</p>
        
        <a href="mailto:common.jaemin@gmail.com" class="contact-btn">
            <i class="fa-solid fa-envelope"></i> Contact Me
        </a>
        
        <div class="social-links">
            <a href="https://www.threads.com/@camorix.official" target="_blank" class="social-item">
                <i class="fa-brands fa-threads"></i> Threads
            </a>
            <a href="https://www.instagram.com/camorix.official/" target="_blank" class="social-item">
                <i class="fa-brands fa-instagram"></i> Instagram
            </a>
            <a href="https://github.com/jjxxmiin" target="_blank" class="social-item">
                <i class="fa-brands fa-github"></i> GitHub
            </a>
            <a href="https://scholar.google.com/citations?user=_GXtE-IAAAAJ&hl=ko" target="_blank" class="social-item">
                <i class="fa-solid fa-graduation-cap"></i> Scholar
            </a>
            <a href="https://www.slideshare.net/JAEMINJEONG5/presentations" target="_blank" class="social-item">
                <i class="fa-brands fa-slideshare"></i> Slides
            </a>
        </div>
    </div>

    <!-- Research Interest -->
    <h2 class="section-title">Research Interests</h2>
    <div class="grid-container">
        <div class="interest-card">
            <div class="interest-icon"><i class="fa-solid fa-eye"></i></div>
            <div class="interest-title">Computer Vision</div>
            <p>Object Detection, Segmentation, GANs, and Video Understanding.</p>
        </div>
        <div class="interest-card">
            <div class="interest-icon"><i class="fa-solid fa-compress"></i></div>
            <div class="interest-title">Model Compression</div>
            <p>Pruning, Quantization, and efficient architecture design for edge devices.</p>
        </div>
        <div class="interest-card">
            <div class="interest-icon"><i class="fa-solid fa-heart-pulse"></i></div>
            <div class="interest-title">Medical AI</div>
            <p>Sleep stage classification using PSG signals and multi-modal analysis.</p>
        </div>
    </div>

    <!-- Skills -->
    <h2 class="section-title">Technical Skills</h2>
    <div style="display: flex; gap: 10px; flex-wrap: wrap;">
        <span class="social-item">Python</span>
        <span class="social-item">PyTorch</span>
        <span class="social-item">TensorFlow</span>
        <span class="social-item">OpenCV</span>
        <span class="social-item">Docker</span>
        <span class="social-item">Git</span>
        <span class="social-item">Raspberry Pi</span>
    </div>

    <!-- Publications -->
    <h2 class="section-title">Selected Publications</h2>
    
    <div class="pub-item">
        <div class="pub-title">Explainable vision transformer for automatic visual sleep staging on multimodal PSG signals</div>
        <div class="pub-authors">Hyojin Lee, You Rim Choi, Hyun Kyung Lee, <span class="pub-me">Jaemin Jeong</span>, et al.</div>
        <div class="pub-venue">Journal of npj Digital Medicine (SCI), 2025</div>
    </div>
    
    <div class="pub-item">
        <div class="pub-title">Optimized Road Damage Detection Using Enhanced Deep Learning Architectures</div>
        <div class="pub-authors"><span class="pub-me">Jaemin Jeong</span>, Jiho Cho, Jeong-Gun Lee</div>
        <div class="pub-venue">2024 IEEE International Conference on Big Data</div>
    </div>

    <div class="pub-item">
        <div class="pub-title">Standardized Image-Based Polysomnography Database and Deep Learning Algorithm</div>
        <div class="pub-authors"><span class="pub-me">Jaemin Jeong</span>, Wonhyuck Yoon, et al.</div>
        <div class="pub-venue">Journal of Oxford SLEEP (SCI), 2023</div>
    </div>
    
    <div style="text-align: right; margin-top: 10px;">
        <a href="https://scholar.google.com/citations?user=_GXtE-IAAAAJ&hl=ko" style="font-weight: 600;">View Full List on Google Scholar &rarr;</a>
    </div>

    <!-- Experience -->
    <h2 class="section-title">Experience</h2>
    <div class="timeline">
        <div class="timeline-item">
            <div class="timeline-date">2023.03 - Present</div>
            <div class="timeline-company">Mirrorroid</div>
            <div class="timeline-role">R&D / Outsourcing</div>
            <div class="timeline-desc">Developing Beauty Smart Mirror solutions (Face/Hair analysis).</div>
        </div>
        <div class="timeline-item">
            <div class="timeline-date">2023.03 - Present</div>
            <div class="timeline-company">University of Ottawa</div>
            <div class="timeline-role">Visiting Research Student (PhD Program)</div>
            <div class="timeline-desc">Researching Model Compression & Sleep Staging.</div>
        </div>
        <div class="timeline-item">
            <div class="timeline-date">2022.03 - 2023.03</div>
            <div class="timeline-company">Mirrorroid</div>
            <div class="timeline-role">Senior Researcher (Full-time)</div>
            <div class="timeline-desc">Led the R&D team for smart beauty technologies.</div>
        </div>
         <div class="timeline-item">
            <div class="timeline-date">2021.03 - 2022.03</div>
            <div class="timeline-company">Hallym University</div>
            <div class="timeline-role">PhD Candidate</div>
            <div class="timeline-desc">Research on deep learning model optimization.</div>
        </div>
    </div>

    <!-- Honors -->
    <h2 class="section-title">Honors & Awards</h2>
    <div style="display: grid; gap: 15px;">
        <div class="pub-item" style="border-left-color: #ff9f43; background: transparent; border: 1px solid #eee;">
            <div class="pub-title">2021 AI+X R&D Challenge Grand Prize (1st)</div>
            <div class="pub-venue">Hallym University</div>
        </div>
         <div class="pub-item" style="border-left-color: #ff9f43; background: transparent; border: 1px solid #eee;">
            <div class="pub-title">2020 NIPA AI Competition 1st Place</div>
            <div class="pub-venue">NIPA (Cybercrime detection model)</div>
        </div>
    </div>

</div>
