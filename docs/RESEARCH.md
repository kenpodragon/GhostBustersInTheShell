# Busting Ghosts in the Machine: Building Open-Source AI Detection From the Ground Up

*By Stephen Salaka*

---

## The Problem

In 2011, I finished my PhD dissertation. Thousands of hours of research, writing, rewriting, and defending my ideas in front of a committee that seemed personally offended by my comma usage. That document sat on a university server for over a decade, bothering nobody. Then in late 2022, ChatGPT happened, and suddenly everyone with an internet connection became an expert on what "sounds like AI." I ran my dissertation through one of the popular commercial detectors on a whim. It came back flagged. My own writing, from years before large language models could string a paragraph together, was apparently "likely AI-generated."

That stung. Not in a devastating way, more in a "this is profoundly stupid" way.

I wasn't alone in this experience. I'd later discover that even cutting-edge neural detectors flag human novels as AI, whole chapters of published fiction getting scored at 100% machine-written. The false positive problem isn't a quirk. It's a feature of how these tools were built.

But here's what really bothered me. I was job hunting at the time, polishing resumes, cover letters, LinkedIn posts. Every piece of professional writing I produced needed to pass through the AI detection gauntlet because recruiters and hiring managers had started screening for it. The commercial tools wanted money per scan. Some charged per document, others ran subscription models. When you're between jobs and submitting dozens of applications a week, paying a detector to tell you whether your own writing sounds human enough is a special kind of absurd.

Perhaps worse than the cost was the opacity. These tools would spit out a number (73% AI probability!) and offer zero explanation of why. What triggered the score? Which sentences? What patterns? You got a black box verdict and a credit card charge. That combination of expensive and unexplainable felt like a problem worth solving.

So I started building my own detector. Open source, running locally, no cloud fees, no per-scan charges, and most importantly, transparent about every single scoring decision it makes.

The name came together naturally. Ghost writers have existed for centuries; there's nothing new about someone else writing your words. But when AI does the ghost writing, something different happens. The machine leaves traces, statistical fingerprints that a human ghost writer wouldn't. Patterns in word choice, sentence structure, the uncanny uniformity of it all. The "ghost" in the machine isn't hiding. It's practically waving. I'd been rewatching Ghost in the Shell around the same time (the 1995 original, obviously), and the mashup wrote itself. GhostBusters In The Shell. We're busting the robotic tells that AI ghost writing leaves behind.

What I didn't expect was how deep the rabbit hole would go. What started as a weekend project to scratch my own itch turned into 68+ detection patterns, a voice profiling system, and arguably the most transparent AI scoring engine I've seen anywhere. But I'm getting ahead of myself.

---

## The Heuristic Approach

The first decision was the most important one. I could have fine-tuned a classifier, thrown a neural network at the problem, trained on labeled datasets of human versus AI text. That's what the commercial tools do. It's also why they're black boxes. When a transformer tells you something is "78% AI," it can't show you its work. The math lives in millions of floating-point weights that no human can interpret.

I went with rules instead. Hand-written heuristics. Every pattern documented, every weight visible, every scoring decision traceable back to a specific observation about how AI actually writes.

This wasn't some principled stance against machine learning (I use Claude's API elsewhere in the tool for rewrites). It was practical. Rule-based detection means the whole thing runs locally. No cloud calls during analysis, no API fees, no sending your text to someone else's server. And when a sentence gets flagged, you can see exactly which pattern triggered it and how many points it contributed. Try getting that from GPTZero.

The system grew to 68+ patterns organized across three tiers. At the sentence level, we check for buzzwords that AI models seem pathologically attracted to ("delve," "tapestry," "leverage," "foster"), hedge word clustering where too many qualifiers pile up in one sentence, transition word overuse, and cross-model phrase fingerprinting that catches constructions specific to Claude versus GPT versus Gemini. At the paragraph level, we measure uniformity (are all your paragraphs suspiciously similar in length?), detect fragment lists masquerading as punchy writing, and flag staccato rhythm patterns. At the document level, we calculate burstiness through sentence length variance, type-token ratio for vocabulary richness, semantic embedding monotony, and chunked score consistency to catch text that scores identically across every 300-word block.

I call it the "Red Car Test." Someone tells you to watch for red cars on your drive home. Suddenly, red cars are everywhere. They were always there; you just weren't looking. Once somebody points out that AI text loves the word "delve," you'll see it in every ChatGPT output for the rest of your life. Once you notice the construction "This is not just X, it's Y," you can't unsee it. These patterns were always there. We just needed to catalog them.

The composite score weights each tier: sentence-level patterns contribute 45%, paragraph-level 30%, document-level 25%. Every single weight is configurable and visible in the scoring breakdown. You can inspect the math for any analysis, see which patterns fired, how many points each contributed, and how the tiers combined into a final score.

Perhaps the most satisfying part is what happens when someone questions a result. Instead of shrugging and saying "the model said so," I can point to the specific line, the specific pattern, and the specific weight. That kind of transparency seems rare in this space. The score math isn't hidden behind an API. It's right there in the report, every coefficient and contribution laid bare for anyone who wants to look.

---

## Voice Profiles as Defense

Detection tells you what's wrong. It doesn't fix anything.

That's the half of this problem that most tools ignore entirely. You run your text through a detector, it highlights suspicious sentences, and then what? You're on your own. Rewrite it yourself, I guess. Hope you get it right this time. Run it through the detector again, pay another scan fee, repeat until broke or frustrated.

Generic paraphrasing tools make the situation worse. They'll take your flagged text and rephrase it, sure, but they replace one set of AI patterns with another. The output still sounds like a machine wrote it; it just sounds like a different machine. I watched this happen repeatedly during testing. Text that scored 45 on our detector would get "paraphrased" by a commercial tool and come back scoring 38. Congratulations, you paid money to move from "AI-touched" to "slightly less AI-touched."

The fix, it turned out, was voice profiles.

The idea is simple enough. Instead of telling a rewriter "make this sound human" (which is meaningless, since AI already thinks it sounds human), you tell it "make this sound like this specific human." A voice profile captures a writer's actual fingerprint from samples of their real writing. We recommend at least 500 words of source material, though 2000+ words gives much better results.

The profile extraction pulls 65+ style elements from those samples. Vocabulary richness measured through type-token ratio. Sentence structure distributions, specifically how often you write short versus long sentences and what your average looks like. Punctuation habits, whether you favor ellipses or semicolons or parenthetical asides (guilty on that last one). Tone markers like formality level, contraction frequency, pronoun usage. Even construction patterns, the recurring syntactic shapes that make your writing yours.

When the rewriter runs, it doesn't just "humanize" the text. It applies your voice profile as a style constraint. The difference is night and day. Generic humanization might turn "leverage synergies to facilitate outcomes" into "use teamwork to get results." A voice-profiled rewrite turns it into whatever you would actually say, with your sentence rhythms, your word choices, your weird habit of starting paragraphs with sentence fragments.

But how do you know the rewrite actually worked? We built evasion metrics for that. After every rewrite, the system calculates a divergence score using cosine similarity on sentence embeddings and an n-gram overlap score using rapidfuzz fuzzy matching. These numbers tell you whether the rewrite genuinely restructured the text or just shuffled words around. If the divergence score comes back below 0.15, a second rewrite pass fires automatically with aggressive structural changes. No human intervention needed.

There's one more piece that might be my favorite feature. The voice style prompt endpoint lets any external tool fetch your exact writing style as an 11.4KB prompt. Other projects, other AI tools, other writing contexts can all pull that prompt and write in your voice. The profile isn't locked inside the detector. It's portable, reusable, yours...

That portability matters. Detection without correction is just expensive anxiety. Correction without your actual voice is just different-flavored AI. The whole system only works when both halves talk to each other.

---

## The Pangram Investigation

At some point I had to face the obvious question. If my heuristics are so transparent and explainable, how do they stack up against a real neural detector? Not one of the pay-per-scan black boxes, but a serious research-backed classifier with published papers and open-sourced models. I needed a reality check.

Enter Pangram Labs. Their platform at pangram.com runs a Mistral NeMo classifier, roughly 12 billion parameters, trained on over 28 million documents. Their technical report (arXiv:2402.14873) describes an approach they call "hard negative mining with synthetic mirrors." The concept is clever. For every human document in the training set, they generate an AI-written version that matches the topic, length, and style. Then they run the model against millions of human examples, collect all the false positives, generate mirror documents for those specific failures, and retrain. Over and over. This iterative process forces the model past surface-level features and into deeper statistical territory that rule-based systems like mine simply cannot reach.

They process text in 512-token chunks, roughly 300 words per segment. And they explicitly reject perplexity and burstiness as detection signals. Too many false positives on formulaic human writing. Their report notes that the Declaration of Independence triggers perplexity-based detectors. Which is both hilarious and telling.

Two companion papers caught my attention. EditLens (arXiv:2510.03154, accepted at ICLR 2026) introduces a regression model that scores text on a continuous scale from 0.0 (fully human) to 1.0 (fully AI-generated). It uses cosine distance between embeddings plus soft n-gram scoring, and the team open-sourced a RoBERTa-Large implementation on HuggingFace. The DAMAGE paper (arXiv:2501.03437) went after humanizer tools specifically, studying 19 of them and building a classifier that maintained 93.2% true positive rate even on humanized text. That number stuck with me.

So I tested. Three documents, three very different results.

First, I took a voice-profiled rewrite that our own system scored at 11.5, firmly in the Clean zone. Every heuristic said this text was fine. I submitted it to Pangram. The verdict came back: 100% AI Generated. Not 60%, not "mixed signals." One hundred percent. Our heuristics had missed whatever sub-surface statistical patterns their neural model was picking up. That was humbling.

Second test. I submitted the opening chapter of a novel I started writing in 2019. This is my own fiction, written three years before ChatGPT even existed (late November 2022, for anyone keeping score). Pangram's result: 100% AI Generated. A false positive on text that predates the technology it's supposedly detecting.

Third test. Human fiction from 2005, a different style entirely, more baroque, more idiosyncratic. Pangram scored it 100% Human Written. Correct.

The pattern was hard to ignore.

Modern polished human writing occupies the same embedding space as AI-generated text, because the AI was trained on modern human text. We taught the machines to write like us, and now the detectors can't tell us apart. Older writing with stranger rhythms and weirder vocabulary choices registers as human precisely because it's unusual enough to fall outside the AI distribution. That temporal bias seems baked into every neural detector, not just Pangram's. As writing styles converge over time, this problem only gets worse.

The takeaway wasn't that Pangram is bad. It caught real patterns in AI text that my heuristics completely missed. The takeaway was that neural detection alone isn't enough either. You need both approaches, and you need the heuristic layer to provide the transparency that neural classifiers can't offer. When a neural model says "100% AI" about a human novel from 2019, somebody needs to be able to show their work. That's where rules still win.

---

## Bringing Neural Detection Local

After getting humbled by Pangram's classifier, the next question was obvious. Could I bring that kind of neural detection onto my own machine? No cloud calls. No per-scan fees. No sending my text to someone else's servers for judgment.

Pangram made this possible by open-sourcing their EditLens RoBERTa-Large model on HuggingFace. That model, the same one from the ICLR 2026 paper, can run inference locally. I designed it as an optional Docker sidecar that sits alongside the main application stack.

The architecture has two sidecars. The embeddings sidecar runs all-MiniLM-L6-v2, a 384-dimensional sentence transformer that powers the new embedding-based heuristics. It starts by default with the regular stack. The RoBERTa sidecar is opt-in, activated via `--profile research` in Docker Compose, and it requires a HuggingFace account because the model sits behind a gated repository. The distinction matters. Embeddings are lightweight and useful for everyone. RoBERTa is heavier and aimed at researchers who want the full detection pipeline.

Scoring now uses a triple blend when all components are available. Heuristic analysis contributes 35%, Claude AI analysis contributes 35%, and RoBERTa classification contributes the remaining 30%. But the system degrades gracefully. If you don't have Claude API access, heuristics carry the full weight. Add Claude and you get a 50/50 split. Add RoBERTa and all three share the load. You're never locked out of functionality because you lack one component.

The embeddings sidecar also enabled three new Pangram-inspired heuristics that weren't possible before. Semantic embedding monotony measures mean pairwise similarity across sentence embeddings. AI text tends to maintain eerily consistent semantic density from sentence to sentence, where human writing wanders. Chunked score consistency breaks text into roughly 300-word segments and measures how uniform the detection scores are across chunks. Real coefficient of variation analysis. AI-generated documents score almost identically across every chunk, while human writing varies because we have good paragraphs and bad paragraphs, focused sections and meandering ones. Cross-model phrase fingerprinting uses curated dictionaries of constructions unique to Claude, GPT, and Gemini. Remember the Red Car Test from earlier? Once you catalog the specific phrases each model favors, you start seeing them everywhere.

These three heuristics currently detect and report their findings, but their scoring weights are set to 0.0. They fire, they flag, they show up in the analysis breakdown. They just don't affect the composite score yet. I'm waiting to calibrate them against a proper test corpus before I let them influence real results. Perhaps that's overcautious, but I'd rather have accurate weights than fast ones.

One `docker compose up -d` still gets you the full stack. The sidecar downloads its model on first build and caches it in a Docker volume. After that initial pull, startup takes seconds. Everything stays local.

---

## Evasion Metrics

A rewrite that scores well on detection but just shuffled the same words around hasn't actually fixed anything. It passed the test without doing the work. I needed a way to measure whether a rewrite genuinely transformed the text or merely rearranged the furniture.

Two metrics handle this. N-gram overlap uses rapidfuzz fuzzy matching on 3-grams through 6-grams with a token-level blend at 30/70 weighting. The fuzzy matching catches synonym substitutions that exact matching would miss entirely. If you swap "utilize" for "use," an exact n-gram comparison sees completely different text, but fuzzy matching recognizes the structural similarity. The token-level blend gives higher weight to longer n-grams because preserving a 6-gram sequence is a stronger signal of insufficient rewriting than preserving a 3-gram.

Divergence score measures how far the rewrite moved from the original in semantic space. It calculates 1 minus cosine similarity using MiniLM embeddings from the sidecar, with a Jaccard distance fallback when embeddings aren't available. The thresholds are straightforward: below 0.15 is low divergence (too similar to the original, basically a light edit), 0.15 to 0.35 is moderate, and above 0.35 is high divergence (genuinely restructured). When divergence comes back low, a second rewrite pass fires automatically with aggressive structural changes. More sentence combining, different paragraph breaks, reorganized argument flow. No manual intervention required.

The UI displays both metrics after every rewrite, right alongside the detection scores. You see the before and after in one view. Did the score drop? Good. Did the text actually change? Also good. Did the score drop but the text barely moved? That's a problem, and now you know about it.

---

## Open Source, Local First

The philosophy behind all of this is stubborn and simple. Your text should never have to leave your machine for you to know whether it sounds like a robot wrote it.

No cloud dependency is required to run the core detection engine. No per-scan fees accumulate while you're iterating on a cover letter at midnight. The score math panel shows every weight, every contribution, every pattern that fired and why. If you disagree with a result, you can trace the exact path from raw text to final score and decide for yourself whether the detection got it right. That transparency isn't a feature. It's the point.

The MCP server exposes 20+ tools for integration with any AI agent that speaks the protocol. `analyze_text`, `rewrite_text`, `get_score`, `check_voice`, voice profile management, corpus management, settings configuration. I've already wired it into two other projects through their `.mcp.json` configs, and it took about five minutes each time. The voice style prompt endpoint (GET `/api/voice-style-prompt?baseline_id=1295`) returns that 11.4KB prompt I mentioned earlier, the one that captures your exact writing voice. Other tools pull that prompt and generate text in your style without needing the full 1.8MB profile JSON. It's the lightest-weight integration path available.

There's a Chrome extension too. Manifest V3, runs in the browser, lets you scan any page for AI patterns, generate text in your voice profile, and view full detection reports without leaving whatever site you're on.

The whole stack runs through Docker Compose. One command, `docker compose up -d`, brings up the Flask backend, React frontend, PostgreSQL database, and embeddings sidecar. Everything binds to localhost. Your text never touches an external server unless you explicitly opt into Claude AI analysis through the Anthropic API, and even then, that's your API key on your machine making calls you chose to make.

The code is on GitHub at github.com/kenpodragon/GhostBustersInTheShell under the MIT license. Fork it, modify it, run it on an air-gapped machine if that's your thing. The detection rules, the voice profiling system, the evasion metrics, the scoring math... all of it is yours to inspect, question, and improve. Because if you can't see how the score was calculated, why would you trust it?
