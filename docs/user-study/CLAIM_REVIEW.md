# Limited claim review

This is an agent-assisted review of selected main ideas, not independent human scientific validation. Reviewed 28 October 2026 against linked original-paper descriptions. All ten target titles were found in the final saved reports, after documented iterations. Earlier biomedical runs missed the original; exact-title Crossref retrieval corrected those misses. Repeated attempts remain in results.json.

| Case | Selected comparison | Assessment and limitation |
|---|---|---|
| UC01 | Transformer replaces recurrent/convolutional sequence components with attention. | Main idea agrees with the original abstract. Later-work summaries not exhaustively audited. |
| UC02 | BERT uses bidirectional pretraining and masked prediction. | Main idea agrees; the overview omits next-sentence prediction, so it is not a complete account of the requested objectives. Matrix benchmark values agree with the original abstract. |
| UC03 | RAG combines parametric generation and retrieved external memory. | Main idea agrees. The overview could be more precise about the dense Wikipedia index and sequence/token formulations. |
| UC04 | Residual functions ease optimization of deeper networks. | Main idea agrees; it does not establish that arbitrary additional depth always improves accuracy. |
| UC05 | LoRA freezes pretrained weights and trains low-rank updates. | Main idea agrees. Related variants and efficiency magnitudes were not comprehensively audited. |
| UC06 | GAT uses masked neighbourhood attention with differing neighbour weights. | Main idea agrees. Generated author spelling is imperfect; use retrieved bibliographic metadata, not synthesis prose, for attribution. |
| UC07 | HNSW uses a multilayer hierarchy for approximate neighbour search. | Main idea agrees. No exact-nearest-neighbour guarantee was established. |
| UC08 | AlphaFold predicts protein structures with high reported accuracy. | Original identity retrieved via Crossref. Claims about later models and generalization need separate review; publisher full text was not verified through the web tool. |
| UC09 | RNA-guided endonuclease provides programmable sequence targeting. | Overview is relevant but does not fully explain crRNA/tracrRNA/chimeric RNA. The generated manuscript blurred RNA roles and PAM recognition and inferred missing study scope from excerpts. Flagged; prompting was tightened, not declared scientifically solved. |
| UC10 | Surface codes use stabilizers and physical/logical qubits for error correction. | Main idea agrees. Claims about later experiments require their own source review and are not proof of deployed universal fault tolerance. |

## Uploaded original paper

A 15-page, 2,215,244-byte PDF of Attention Is All You Need was downloaded from arXiv and uploaded through the normal file chooser. The application extracted the title and generated a related-literature comparison. The initial comparison recommended later Transformer variants as missing references and treated absent excerpt details as absent paper content. These are unreliable review inferences. The prompt now distinguishes excerpt absence from refutation and prohibits anachronistic citation criticism; the UI labels its limited scope. A second UI upload with the revised prompt produced questions for the full paper rather than definitive accusations about missing experiments, and displayed the scope notice. This is a control improvement, not evidence of complete review accuracy.

## Sources used for the selected comparisons

- Transformer: https://arxiv.org/abs/1706.03762
- BERT: https://arxiv.org/abs/1810.04805
- RAG: https://arxiv.org/abs/2005.11401
- ResNet: https://arxiv.org/abs/1512.03385
- LoRA: https://arxiv.org/abs/2106.09685
- GAT: https://arxiv.org/abs/1710.10903
- HNSW: https://arxiv.org/abs/1603.09320
- AlphaFold identity: https://doi.org/10.1038/s41586-021-03819-2
- CRISPR identity: https://doi.org/10.1126/science.1225829
- Surface codes: https://arxiv.org/abs/1208.0928

The original abstract pages for the eight arXiv cases were read through the web tool. The Nature page could not be fetched and PubMed presented a browser check; Crossref/app metadata supported identity, not full-paper validation. No full published paper text is redistributed here.
