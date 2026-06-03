# ForageBench — Project Page (gh-pages)

Static project page for **ForageBench: A Photorealistic, Physically Grounded Benchmark
for Interactive Object Search** (University of Michigan). Plain HTML/CSS/JS.

These files are the **website** and live on the `gh-pages` branch of the
`m-and-m-lab/ForageBench` repo. The interactive-search code goes on `main` later.

Live URL: **https://m-and-m-lab.github.io/ForageBench/**  (case-sensitive)

```
index.html  styles.css  .nojekyll  README.md
assets/  (js, images, papers/foragebench.pdf, qr, ...)   scripts/make_qr.py
```

## Deploy to the gh-pages branch
GitHub Pages requires the repo to be **public**. To publish the page now while the
interactive-search code stays unreleased, keep `main` as a placeholder (e.g. a README
that says "code coming soon") and put only the website on `gh-pages`:

```bash
git clone https://github.com/m-and-m-lab/ForageBench.git ForageBench-page
cd ForageBench-page
git checkout --orphan gh-pages
git rm -rf .
cp -r /path/to/foragebench-site/. .
git add .
git commit -m "ForageBench project page"
git push -u origin gh-pages
```
Then: **Settings → Pages → Source: Deploy from a branch → `gh-pages` / `(root)`**.
Live at the URL above. The hero "Code (coming soon)" button stays disabled until you
push the real code to `main` and flip it to a link.

## Add figures / videos
Export `teaser.png` (Fig 1) and `scenes.png` (Fig 2) into `assets/images/`; add
`sim_*` / `real_spot_*` clips to `assets/videos/`. Swap each placeholder for the
commented `<video>` snippet (files < 100 MB).

## QR (standalone, not on the page)
`python scripts/make_qr.py "https://m-and-m-lab.github.io/ForageBench/"` → `assets/qr/project_qr.png`.
