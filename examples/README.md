# Example queues — the pipeline as three files

These mirror the three stages of the factory, generated from the real demo run, so you can **see or demo each hand-off** (great for the "where's the human in the loop?" moment on camera):

1. **[1-explore-queue.md](1-explore-queue.md)** — the 20 products queued to **explore** (the input). The factory fans out a worker pool and generates + vision-scores two ad concepts per product.
2. **[2-review-queue.md](2-review-queue.md)** — the 39 scored concepts awaiting the **one human step**: you approve the ones worth turning into video.
3. **[3-approved-queue.md](3-approved-queue.md)** — the 12 **approved** winners; each gets rendered into a product pan + a UGC talking-head.

`Explore cheap → approve human → render only winners.`
