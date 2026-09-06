export const meta = {
  name: 'ig-verbatim-frames',
  description: 'Verbatim on-screen OCR across candidate frames + pick the 3 most distinct frames (catch the punchline) per reel',
  phases: [{ title: 'OCR+Pick' }],
}

// Data directory is resolved relative to the repo root by default; override
// with the IG_DATA_DIR env var if you invoke this workflow from elsewhere.
const BASE = (typeof env !== 'undefined' && env.IG_DATA_DIR) || 'data'
const INDEX = BASE + "/candidates_index.json"
const BATCH_SIZE = 6

// Every shortcode present in candidates_index.json gets processed. Restrict to
// a subset by setting IG_SHORTCODES to a comma-separated list (e.g. for a
// pilot run on your first few captures) instead of hand-editing this file.
const index = JSON.parse(await readFile(INDEX, 'utf-8'))
const restrict = (typeof env !== 'undefined' && env.IG_SHORTCODES) ? env.IG_SHORTCODES.split(',').map(s => s.trim()).filter(Boolean) : null
const SCS = restrict || Object.keys(index)

const SCHEMA = { type:"object", properties:{ items:{ type:"array", items:{ type:"object", properties:{
  shortcode:{type:"string"},
  onscreen_text:{type:"string", description:"ALL on-screen overlay text across the frames, VERBATIM in original script (Devanagari stays Devanagari, Hinglish stays Latin, keep emojis/spelling). Order hook->punchline, separate distinct states with ' / '. Empty if truly none."},
  keep_frames:{type:"array", items:{type:"string"}, description:"Up to 3 candidate paths (from the index, relative form) that best show the DISTINCT text/visual states incl. the punchline. Ordered by appearance."}
}, required:["shortcode","onscreen_text","keep_frames"] } } }, required:["items"] }

const batches = []
for (let i = 0; i < SCS.length; i += BATCH_SIZE) batches.push(SCS.slice(i, i + BATCH_SIZE))

const results = await parallel(batches.map((batch,i)=>()=>
  agent(
    `You extract VERBATIM on-screen text and pick key frames from saved Instagram reels.\n`+
    `Read ${INDEX} (JSON: shortcode -> {slug, candidates:[relative image paths]}). Candidate paths are relative to ${BASE}/ — Read each as ${BASE}/<relative>.\n\n`+
    `Process EXACTLY these shortcodes: ${JSON.stringify(batch)}.\n`+
    `For each shortcode: Read ALL its candidate frames (they are time-ordered samples + scene cuts of the reel). Then:\n`+
    `1) onscreen_text = transcribe EVERY overlay text you see, VERBATIM, in its ORIGINAL language/script — do NOT translate or romanize (Hindi->Devanagari, Hinglish->as written, English->English), keep emojis and exact spelling. Capture the full progression including any later PUNCHLINE/reveal. Join distinct text states with ' / '. If a frame repeats the same text, don't duplicate. If there is genuinely no overlay text, return "".\n`+
    `2) keep_frames = choose up to 3 candidate paths (relative, exactly as in the index) that together best show the distinct states — the hook, any transition, and the punchline. If fewer distinct states, return fewer. If a clip has no candidates, return [].\n`+
    `Return one item per shortcode.`,
    { label:`ocr:${i+1}`, phase:'OCR+Pick', schema:SCHEMA }
  ).then(r=> (r&&r.items)?r.items:[])
))

const flat = results.filter(Boolean).flat()
return { count: flat.length, items: flat }
