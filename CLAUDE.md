# arielle-autopost

Automated Instagram posting for @iamariellenova. Read `brand/arielle.md` before writing any content.

## How it works
- Each post is a folder `posts/queue/YYYY-MM-DD-slug/` with a `post.json` (see `examples/`).
- `scripts/render.py` turns the slides in post.json into `01.jpg, 02.jpg …` (1080x1350).
- `.github/workflows/publish.yml` runs hourly and publishes every post whose `publish_at` has passed,
  then moves it to `posts/published/`. Never edit or delete anything in `posts/published/`.
- Only content merged into `main` gets published. New weeks always go through a pull request so
  Shelley can approve them first.

## post.json
- `publish_at`: ISO time with offset, Europe/Amsterdam (`+01:00` in winter, `+02:00` in summer).
- `caption`: full caption incl. hashtags and the closing `✦ AI-generated creator` line. ≤2200 chars, ≤30 hashtags.
- `slides`: list of slides. Types: `cover`, `text`, `quote`, `cta`, `photo` (`image` = path under assets/photos, optional `title`).
  One slide = single-image post; 2–10 slides = carousel.

## Weekly routine (scheduled every Sunday)
1. `git pull`. Look at `posts/published/` and `posts/queue/` to avoid repeating topics or photos.
2. Check the coming week (Mon–Sun) for relevant moments: holidays, seasons, big AI/tech news (search the web), money moments
   (payday, Black Friday, New Year). Use them when they fit Arielle's pillars; never force it.
3. Write 5 posts for Mon–Sun across all four pillars. Good times: 12:30 or 18:30 on weekdays, 10:00 on weekends.
4. Create branch `week-YYYY-WW`, add the folders, run `python scripts/render.py --all`, look at every rendered image
   (text must fit, no overlaps), commit and push.
5. Open a PR titled `Week WW: <short theme>` whose description shows, per post: day/time, the caption, and the images as
   `![](https://raw.githubusercontent.com/hellovascostudio/arielle-autopost/<branch>/posts/queue/<folder>/01.jpg)`.
   End with: "Merge om deze week in te plannen. Wil je iets anders? Reageer hier of in Claude."
6. Never merge it yourself and never publish directly.
