const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, LevelFormat,
  HeadingLevel, BorderStyle, WidthType, ShadingType,
  PageNumber, PageBreak, TabStopType, TabStopPosition,
  FootnoteReferenceRun
} = require("docx");

// ── Helpers ──────────────────────────────────────────────────────────────────
const CONTENT_WIDTH = 9360; // US Letter 8.5" with 1" margins
const noBorder = { style: BorderStyle.NONE, size: 0 };
const noBorders = { top: noBorder, bottom: noBorder, left: noBorder, right: noBorder };
const thinBorder = { style: BorderStyle.SINGLE, size: 1, color: "999999" };
const tableBorders = { top: thinBorder, bottom: thinBorder, left: thinBorder, right: thinBorder };

function p(text, opts = {}) {
  const runs = [];
  if (typeof text === "string") {
    runs.push(new TextRun({ text, ...opts }));
  } else if (Array.isArray(text)) {
    text.forEach(t => {
      if (typeof t === "string") runs.push(new TextRun({ text: t }));
      else runs.push(new TextRun(t));
    });
  }
  return new Paragraph({
    spacing: { after: opts.spacingAfter || 200, line: opts.lineSpacing || 480 },
    alignment: opts.alignment || AlignmentType.JUSTIFIED,
    children: runs,
    ...(opts.paragraphOpts || {})
  });
}

function heading(text, level, opts = {}) {
  return new Paragraph({
    heading: level,
    spacing: { before: opts.before || 360, after: opts.after || 200 },
    alignment: opts.alignment || AlignmentType.LEFT,
    children: [new TextRun({ text, bold: true, font: "Times New Roman",
      size: level === HeadingLevel.HEADING_1 ? 28 : level === HeadingLevel.HEADING_2 ? 26 : 24 })],
  });
}

function emptyLine() {
  return new Paragraph({ spacing: { after: 100 }, children: [] });
}

function tableRow(cells, isHeader = false) {
  return new TableRow({
    tableHeader: isHeader,
    children: cells.map((cell, i) => {
      const width = cell.width || Math.floor(CONTENT_WIDTH / cells.length);
      return new TableCell({
        borders: tableBorders,
        width: { size: width, type: WidthType.DXA },
        shading: isHeader ? { fill: "D9E2F3", type: ShadingType.CLEAR } : undefined,
        margins: { top: 60, bottom: 60, left: 100, right: 100 },
        verticalAlign: "center",
        children: [new Paragraph({
          spacing: { after: 0, line: 276 },
          alignment: cell.align || AlignmentType.LEFT,
          children: [new TextRun({
            text: cell.text || cell,
            bold: isHeader,
            font: "Times New Roman",
            size: 20,
          })]
        })]
      });
    })
  });
}

// ── Footnotes ────────────────────────────────────────────────────────────────
const footnotes = {};
const refs = [
  "Apfelbaum JL, Connis RT, Nickinovich DG, et al. Practice advisory for preanesthesia evaluation: an updated report by the American Society of Anesthesiologists Task Force on Preanesthesia Evaluation. Anesthesiology. 2012;116(3):522-538.",
  "Kash BA, Smalley MA, Forbes LM, et al. Reviewing the evidence for the use of anesthesia information management systems. Anesthesiol Res Pract. 2011;2011:476543.",
  "Roshanov PS, Rochwerg B, Patel A, et al. Withholding versus continuing angiotensin-converting enzyme inhibitors or angiotensin II receptor blockers before noncardiac surgery. Anesthesiology. 2017;126(1):16-27.",
  "Duggan EW, Carlson K, Umpierrez GE. Perioperative hyperglycemia management: an update. Anesthesiology. 2017;126(3):547-560.",
  "Huang VW, Chang HJ, Kroeker KI, et al. Does preoperative anaemia adversely affect outcome in patients with inflammatory bowel disease undergoing abdominal surgery? Colorectal Dis. 2012;14(9):1045-1049.",
  "Apfelbaum JL, Hagberg CA, Connis RT, et al. 2022 American Society of Anesthesiologists Practice Guidelines for Management of the Difficult Airway. Anesthesiology. 2022;136(1):31-81.",
  "Nightingale CE, Margarson MP, Shearer E, et al. Peri-operative management of the obese surgical patient 2015. Anaesthesia. 2015;70(7):859-876.",
  "Ratwani RM, Hodgkins M, Bates DW. Improving electronic health record usability and safety requires transparency. JAMA. 2018;320(24):2533-2534.",
  "Johnson AE, Pollard TJ, Shen L, et al. MIMIC-III, a freely accessible critical care database. Sci Data. 2016;3:160035.",
  "Esteva A, Robicquet A, Ramsundar B, et al. A guide to deep learning in healthcare. Nat Med. 2019;25(1):24-29.",
  "Rajkomar A, Dean J, Kohane I. Machine learning in medicine. N Engl J Med. 2019;380(14):1347-1358.",
  "Alsentzer E, Murphy JR, Boag W, et al. Publicly available clinical BERT embeddings. arXiv preprint arXiv:1904.03323. 2019.",
  "Lewis P, Perez E, Piktus A, et al. Retrieval-augmented generation for knowledge-intensive NLP tasks. Advances in Neural Information Processing Systems. 2020;33:9459-9474.",
  "Huang K, Altosaar J, Ranganath R. ClinicalBERT: Modeling clinical notes and predicting hospital readmission. arXiv preprint arXiv:1904.05342. 2019.",
  "Devlin J, Chang MW, Lee K, Toutanova K. BERT: Pre-training of deep bidirectional transformers for language understanding. Proceedings of NAACL-HLT. 2019:4171-4186.",
  "Malkov YA, Yashunin DA. Efficient and robust approximate nearest neighbor search using Hierarchical Navigable Small World graphs. IEEE Trans Pattern Anal Mach Inttic. 2020;42(4):824-836.",
  "Lee J, Yoon W, Kim S, et al. BioBERT: a pre-trained biomedical language representation model for biomedical text mining. Bioinformatics. 2020;36(4):1234-1240.",
  "Gu Y, Tinn R, Cheng H, et al. Domain-specific language model pretraining for biomedical natural language processing. ACM Trans Comput Healthcare. 2022;3(1):1-23.",
  "Thirunavukarasu AJ, Ting DSJ, Elangovan K, et al. Large language models in medicine. Nat Med. 2023;29(8):1930-1940.",
  "Gao Y, Xiong Y, Vijayakumar A, et al. Retrieval-augmented generation for large language models: a survey. arXiv preprint arXiv:2312.10997. 2023.",
  "Singhal K, Azizi S, Tu T, et al. Large language models encode clinical knowledge. Nature. 2023;620(7972):172-180.",
  "Nori H, King N, McKinney SM, et al. Capabilities of GPT-4 on medical competency examinations. arXiv preprint arXiv:2303.13375. 2023.",
  "Vaswani A, Shazeer N, Parmar N, et al. Attention is all you need. Advances in Neural Information Processing Systems. 2017;30:5998-6008.",
  "Fleisher LA, Fleischmann KE, Auerbach AD, et al. 2014 ACC/AHA guideline on perioperative cardiovascular evaluation and management of patients undergoing noncardiac surgery. J Am Coll Cardiol. 2014;64(22):e77-e137."
];

for (let i = 0; i < refs.length; i++) {
  footnotes[i + 1] = { children: [new Paragraph({ children: [new TextRun({ text: refs[i], font: "Times New Roman", size: 18 })] })] };
}

// ── Build Document ───────────────────────────────────────────────────────────
const doc = new Document({
  styles: {
    default: {
      document: { run: { font: "Times New Roman", size: 24 } } // 12pt
    },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: "Times New Roman" },
        paragraph: { spacing: { before: 360, after: 200 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, font: "Times New Roman" },
        paragraph: { spacing: { before: 300, after: 180 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, font: "Times New Roman", italics: true },
        paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 2 } },
    ]
  },
  numbering: {
    config: [
      { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "numbers", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "numbers2", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "numbers3", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "numbers4", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    ]
  },
  footnotes,
  sections: [
    // ══════════════════════════════════════════════════════════════════════════
    // TITLE PAGE
    // ══════════════════════════════════════════════════════════════════════════
    {
      properties: {
        page: {
          size: { width: 12240, height: 15840 },
          margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
        }
      },
      headers: {
        default: new Header({ children: [new Paragraph({
          alignment: AlignmentType.RIGHT,
          children: [new TextRun({ text: "RAG-ClinicalBERT for Preoperative Assessment", font: "Times New Roman", size: 18, italics: true, color: "666666" })]
        })] })
      },
      footers: {
        default: new Footer({ children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ children: [PageNumber.CURRENT], font: "Times New Roman", size: 20 })]
        })] })
      },
      children: [
        emptyLine(), emptyLine(), emptyLine(),
        new Paragraph({
          spacing: { after: 100, line: 480 },
          alignment: AlignmentType.LEFT,
          children: [new TextRun({ text: "ORIGINAL RESEARCH ARTICLE", font: "Times New Roman", size: 20, bold: true, color: "666666" })]
        }),
        emptyLine(),
        // Title
        new Paragraph({
          spacing: { after: 300, line: 480 },
          alignment: AlignmentType.LEFT,
          children: [new TextRun({ text: "RAG-ClinicalBERT (Nadella): A Retrieval-Augmented Generation System with Domain-Specific Embeddings for Rapid Identification of Critical Comorbidities in Preoperative Anesthesia Assessment", font: "Times New Roman", size: 32, bold: true })]
        }),
        emptyLine(),
        // Running title
        new Paragraph({
          spacing: { after: 200, line: 360 },
          children: [
            new TextRun({ text: "Running Title: ", font: "Times New Roman", size: 22, bold: true }),
            new TextRun({ text: "RAG-ClinicalBERT for Preoperative Comorbidity Identification", font: "Times New Roman", size: 22 })
          ]
        }),
        emptyLine(),
        // Authors
        new Paragraph({
          spacing: { after: 100, line: 360 },
          children: [
            new TextRun({ text: "Sai Nadella, MD", font: "Times New Roman", size: 24, bold: true }),
            new TextRun({ text: "\u00B9", font: "Times New Roman", size: 24, superScript: true }),
          ]
        }),
        emptyLine(),
        // Affiliations
        new Paragraph({
          spacing: { after: 100, line: 360 },
          children: [
            new TextRun({ text: "\u00B9", font: "Times New Roman", size: 20, superScript: true }),
            new TextRun({ text: " Department of Anesthesiology, [Institution]", font: "Times New Roman", size: 20 })
          ]
        }),
        emptyLine(),
        // Correspondence
        new Paragraph({
          spacing: { after: 100, line: 360 },
          children: [
            new TextRun({ text: "Corresponding Author: ", font: "Times New Roman", size: 22, bold: true }),
            new TextRun({ text: "Sai Nadella, MD", font: "Times New Roman", size: 22 })
          ]
        }),
        new Paragraph({
          spacing: { after: 100, line: 360 },
          children: [new TextRun({ text: "Department of Anesthesiology, [Institution]", font: "Times New Roman", size: 22 })]
        }),
        new Paragraph({
          spacing: { after: 100, line: 360 },
          children: [new TextRun({ text: "Email: [corresponding author email]", font: "Times New Roman", size: 22 })]
        }),
        emptyLine(), emptyLine(),
        // Word count / key info
        new Paragraph({
          spacing: { after: 100, line: 360 },
          children: [
            new TextRun({ text: "Word Count: ", font: "Times New Roman", size: 20, bold: true }),
            new TextRun({ text: "~4,200 (excluding abstract, references, tables, and figures)", font: "Times New Roman", size: 20 })
          ]
        }),
        new Paragraph({
          spacing: { after: 100, line: 360 },
          children: [
            new TextRun({ text: "Tables: ", font: "Times New Roman", size: 20, bold: true }),
            new TextRun({ text: "4  |  ", font: "Times New Roman", size: 20 }),
            new TextRun({ text: "Figures: ", font: "Times New Roman", size: 20, bold: true }),
            new TextRun({ text: "3  |  ", font: "Times New Roman", size: 20 }),
            new TextRun({ text: "References: ", font: "Times New Roman", size: 20, bold: true }),
            new TextRun({ text: "24", font: "Times New Roman", size: 20 })
          ]
        }),
        emptyLine(),
        new Paragraph({
          spacing: { after: 100, line: 360 },
          children: [
            new TextRun({ text: "Conflicts of Interest: ", font: "Times New Roman", size: 20, bold: true }),
            new TextRun({ text: "The author declares no conflicts of interest.", font: "Times New Roman", size: 20 })
          ]
        }),
        new Paragraph({
          spacing: { after: 100, line: 360 },
          children: [
            new TextRun({ text: "Funding: ", font: "Times New Roman", size: 20, bold: true }),
            new TextRun({ text: "No external funding was received for this work.", font: "Times New Roman", size: 20 })
          ]
        }),
      ]
    },

    // ══════════════════════════════════════════════════════════════════════════
    // ABSTRACT
    // ══════════════════════════════════════════════════════════════════════════
    {
      properties: {
        page: {
          size: { width: 12240, height: 15840 },
          margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
        }
      },
      headers: {
        default: new Header({ children: [new Paragraph({
          alignment: AlignmentType.RIGHT,
          children: [new TextRun({ text: "RAG-ClinicalBERT for Preoperative Assessment", font: "Times New Roman", size: 18, italics: true, color: "666666" })]
        })] })
      },
      footers: {
        default: new Footer({ children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ children: [PageNumber.CURRENT], font: "Times New Roman", size: 20 })]
        })] })
      },
      children: [
        heading("ABSTRACT", HeadingLevel.HEADING_1, { alignment: AlignmentType.CENTER }),
        // Background
        new Paragraph({
          spacing: { after: 200, line: 480 },
          alignment: AlignmentType.JUSTIFIED,
          children: [
            new TextRun({ text: "Background: ", font: "Times New Roman", size: 24, bold: true }),
            new TextRun({ text: "Preoperative assessment requires rapid identification of critical comorbidities to formulate safe anesthetic plans. Traditional electronic health record (EHR) review is time-consuming, and keyword-based search systems fail to capture semantic relationships in clinical documentation. We developed RAG-ClinicalBERT (Nadella), a Retrieval-Augmented Generation system using domain-specific medical language model embeddings to rapidly extract anesthesia-relevant comorbidities from medical records.", font: "Times New Roman", size: 24 })
          ]
        }),
        // Methods
        new Paragraph({
          spacing: { after: 200, line: 480 },
          alignment: AlignmentType.JUSTIFIED,
          children: [
            new TextRun({ text: "Methods: ", font: "Times New Roman", size: 24, bold: true }),
            new TextRun({ text: "We developed and evaluated a RAG-based clinical decision support system utilizing ClinicalBERT (Bio_ClinicalBERT) embeddings (768-dimensional vectors) integrated with a Neon PostgreSQL vector database using pgvector with Hierarchical Navigable Small World (HNSW) indexing. The system was evaluated on 1,000 de-identified medical cases (1,680 text chunks) from the MIMIC-III database across five anesthesia-relevant conditions: hypertension, diabetes mellitus, Crohn\u2019s disease, difficult airway, and morbid obesity. Performance was assessed using retrieval accuracy, response time, confidence scoring, and structured information extraction completeness across 46 standardized test queries.", font: "Times New Roman", size: 24 })
          ]
        }),
        // Results
        new Paragraph({
          spacing: { after: 200, line: 480 },
          alignment: AlignmentType.JUSTIFIED,
          children: [
            new TextRun({ text: "Results: ", font: "Times New Roman", size: 24, bold: true }),
            new TextRun({ text: "The system achieved 100% retrieval success across all 46 test queries with a mean cosine similarity score of 0.85 (range: 0.80\u20130.86). Mean query response time was 1.02 seconds (range: 0.04\u20132.01 s), with diagnosis-specific queries completing in 0.10 s (mean) and general symptom queries in 0.53 s (mean). Information extraction rates were 94.3% for diagnoses, 87.6% for medications, 91.5% for chief complaints, and 78.2% for vital signs. The system successfully recognized medical abbreviations (HTN, DM, CAD) and terminology variations, demonstrating semantic understanding beyond exact keyword matching.", font: "Times New Roman", size: 24 })
          ]
        }),
        // Conclusions
        new Paragraph({
          spacing: { after: 200, line: 480 },
          alignment: AlignmentType.JUSTIFIED,
          children: [
            new TextRun({ text: "Conclusions: ", font: "Times New Roman", size: 24, bold: true }),
            new TextRun({ text: "RAG-ClinicalBERT (Nadella) demonstrates the feasibility of using domain-specific language model embeddings with vector similarity search for rapid preoperative comorbidity identification. The sub-2-second response times represent a potential 70\u201390% reduction in information retrieval time compared to traditional chart review. Prospective clinical validation and formal comparison to expert chart review are warranted.", font: "Times New Roman", size: 24 })
          ]
        }),
        emptyLine(),
        // Keywords
        new Paragraph({
          spacing: { after: 200, line: 480 },
          alignment: AlignmentType.JUSTIFIED,
          children: [
            new TextRun({ text: "Keywords: ", font: "Times New Roman", size: 24, bold: true }),
            new TextRun({ text: "Anesthesia; Preoperative Assessment; Retrieval-Augmented Generation; ClinicalBERT; Clinical Decision Support; Natural Language Processing; Vector Database; Comorbidity Identification", font: "Times New Roman", size: 24 })
          ]
        }),

        // ════════════════════════════════════════════════════════════════════
        // 1. INTRODUCTION
        // ════════════════════════════════════════════════════════════════════
        new Paragraph({ children: [new PageBreak()] }),
        heading("1. INTRODUCTION", HeadingLevel.HEADING_1),

        heading("1.1 Background and Rationale", HeadingLevel.HEADING_2),
        new Paragraph({
          spacing: { after: 200, line: 480 },
          alignment: AlignmentType.JUSTIFIED,
          children: [
            new TextRun({ text: "Preoperative anesthetic evaluation is a critical component of perioperative care, requiring comprehensive assessment of patient comorbidities, medications, allergies, and physiologic reserve to formulate safe anesthetic plans.", font: "Times New Roman", size: 24 }),
            new FootnoteReferenceRun(1),
            new TextRun({ text: " Anesthesiologists must rapidly synthesize information from electronic health records (EHRs), operative notes, imaging reports, and laboratory data to identify conditions that significantly impact anesthetic management and patient outcomes.", font: "Times New Roman", size: 24 }),
            new FootnoteReferenceRun(2),
          ]
        }),
        new Paragraph({
          spacing: { after: 200, line: 480 },
          alignment: AlignmentType.JUSTIFIED,
          children: [
            new TextRun({ text: "Certain comorbidities carry particular significance for anesthetic planning. Hypertension affects medication management and hemodynamic stability", font: "Times New Roman", size: 24 }),
            new FootnoteReferenceRun(3),
            new TextRun({ text: "; diabetes mellitus influences metabolic control and perioperative glucose management", font: "Times New Roman", size: 24 }),
            new FootnoteReferenceRun(4),
            new TextRun({ text: "; inflammatory bowel disease such as Crohn\u2019s disease impacts nutritional status and medication interactions", font: "Times New Roman", size: 24 }),
            new FootnoteReferenceRun(5),
            new TextRun({ text: "; difficult airway or intubation history requires specialized equipment and expertise", font: "Times New Roman", size: 24 }),
            new FootnoteReferenceRun(6),
            new TextRun({ text: "; and morbid obesity (BMI \u226540) presents multiple challenges including airway management, positioning, and respiratory complications.", font: "Times New Roman", size: 24 }),
            new FootnoteReferenceRun(7),
          ]
        }),
        new Paragraph({
          spacing: { after: 200, line: 480 },
          alignment: AlignmentType.JUSTIFIED,
          children: [
            new TextRun({ text: "Traditional chart review is time-intensive, with anesthesiologists spending significant clinical time navigating fragmented EHR systems.", font: "Times New Roman", size: 24 }),
            new FootnoteReferenceRun(8),
            new TextRun({ text: " Important clinical details may be buried within extensive documentation, leading to potential oversights. This challenge is amplified in time-sensitive scenarios such as urgent surgical procedures or high-volume preoperative clinics. Keyword-based search within EHRs relies on exact string matching, failing to capture semantic relationships\u2014for example, missing records documenting \u201CHTN\u201D when searching for \u201Chypertension.\u201D", font: "Times New Roman", size: 24 }),
          ]
        }),

        heading("1.2 Artificial Intelligence in Clinical Decision Support", HeadingLevel.HEADING_2),
        new Paragraph({
          spacing: { after: 200, line: 480 },
          alignment: AlignmentType.JUSTIFIED,
          children: [
            new TextRun({ text: "Recent advances in natural language processing (NLP) and transformer-based machine learning architectures", font: "Times New Roman", size: 24 }),
            new FootnoteReferenceRun(23),
            new TextRun({ text: " have enabled development of clinical decision support systems capable of extracting and synthesizing information from unstructured medical text.", font: "Times New Roman", size: 24 }),
            new FootnoteReferenceRun(10),
            new FootnoteReferenceRun(11),
            new TextRun({ text: " Domain-specific language models such as ClinicalBERT, pretrained on large clinical note corpora, demonstrate superior performance in understanding medical terminology compared to general-purpose models.", font: "Times New Roman", size: 24 }),
            new FootnoteReferenceRun(12),
          ]
        }),
        new Paragraph({
          spacing: { after: 200, line: 480 },
          alignment: AlignmentType.JUSTIFIED,
          children: [
            new TextRun({ text: "Retrieval-Augmented Generation (RAG) systems combine semantic search capabilities with contextual information extraction, offering advantages over traditional keyword-based search by understanding semantic relationships rather than relying solely on exact keyword matches.", font: "Times New Roman", size: 24 }),
            new FootnoteReferenceRun(13),
            new FootnoteReferenceRun(20),
            new TextRun({ text: " Large language models have shown promise in encoding clinical knowledge", font: "Times New Roman", size: 24 }),
            new FootnoteReferenceRun(21),
            new TextRun({ text: " and achieving performance on medical competency examinations", font: "Times New Roman", size: 24 }),
            new FootnoteReferenceRun(22),
            new TextRun({ text: ", yet their integration into institutional clinical workflows with verifiable source attribution remains an area of active development.", font: "Times New Roman", size: 24 }),
            new FootnoteReferenceRun(19),
          ]
        }),

        heading("1.3 Study Objectives", HeadingLevel.HEADING_2),
        new Paragraph({
          spacing: { after: 200, line: 480 },
          alignment: AlignmentType.JUSTIFIED,
          children: [
            new TextRun({ text: "The primary objective of this study was to develop and evaluate RAG-ClinicalBERT (Nadella), a Retrieval-Augmented Generation system utilizing domain-specific ClinicalBERT embeddings for rapid identification of anesthesia-relevant comorbidities from medical case databases. Specific aims included:", font: "Times New Roman", size: 24 }),
          ]
        }),
        ...[
          "Develop a RAG system utilizing ClinicalBERT embeddings with vector similarity search via HNSW indexing on a Neon PostgreSQL database",
          "Evaluate system performance in identifying five critical conditions: hypertension, diabetes mellitus, Crohn\u2019s disease, difficult airway, and morbid obesity",
          "Assess response time, similarity-based confidence scoring, and structured clinical information extraction completeness",
          "Demonstrate feasibility of AI-assisted preoperative assessment tools with source-cited retrieval from institutional medical records"
        ].map(item => new Paragraph({
          numbering: { reference: "numbers", level: 0 },
          spacing: { after: 120, line: 480 },
          alignment: AlignmentType.JUSTIFIED,
          children: [new TextRun({ text: item, font: "Times New Roman", size: 24 })]
        })),

        // ════════════════════════════════════════════════════════════════════
        // 2. METHODS
        // ════════════════════════════════════════════════════════════════════
        new Paragraph({ children: [new PageBreak()] }),
        heading("2. METHODS", HeadingLevel.HEADING_1),

        heading("2.1 System Architecture", HeadingLevel.HEADING_2),
        heading("2.1.1 Technical Framework", HeadingLevel.HEADING_3),
        new Paragraph({
          spacing: { after: 200, line: 480 },
          alignment: AlignmentType.JUSTIFIED,
          children: [
            new TextRun({ text: "We developed RAG-ClinicalBERT (Nadella) as a web-based clinical decision support application comprising four core components: (1) ", font: "Times New Roman", size: 24 }),
            new TextRun({ text: "NeonRAGDatabase", font: "Times New Roman", size: 24, bold: true }),
            new TextRun({ text: "\u2014vector database operations using PostgreSQL with pgvector extension for efficient similarity search; (2) ", font: "Times New Roman", size: 24 }),
            new TextRun({ text: "MedicalRAGSystem", font: "Times New Roman", size: 24, bold: true }),
            new TextRun({ text: "\u2014core RAG logic with ClinicalBERT (emilyalsentzer/Bio_ClinicalBERT)", font: "Times New Roman", size: 24 }),
            new FootnoteReferenceRun(12),
            new TextRun({ text: " generating 768-dimensional embeddings; (3) ", font: "Times New Roman", size: 24 }),
            new TextRun({ text: "ProcessingCache", font: "Times New Roman", size: 24, bold: true }),
            new TextRun({ text: "\u2014SQLite-based caching with MD5 hash-based change detection for efficient incremental processing; and (4) a ", font: "Times New Roman", size: 24 }),
            new TextRun({ text: "Web Interface", font: "Times New Roman", size: 24, bold: true }),
            new TextRun({ text: "\u2014Flask-based RESTful API backend with a Next.js frontend for interactive clinical querying.", font: "Times New Roman", size: 24 }),
          ]
        }),
        new Paragraph({
          spacing: { after: 200, line: 480 },
          alignment: AlignmentType.JUSTIFIED,
          children: [
            new TextRun({ text: "ClinicalBERT was selected over alternative models (BioBERT", font: "Times New Roman", size: 24 }),
            new FootnoteReferenceRun(17),
            new TextRun({ text: ", PubMedBERT", font: "Times New Roman", size: 24 }),
            new FootnoteReferenceRun(18),
            new TextRun({ text: ", general BERT", font: "Times New Roman", size: 24 }),
            new FootnoteReferenceRun(15),
            new TextRun({ text: ") because it was pretrained specifically on clinical notes from the MIMIC-III database, providing superior understanding of clinical documentation patterns, abbreviations (e.g., HTN, DM, CAD, CHF), and narrative structures found in discharge summaries, operative reports, and progress notes\u2014the precise document types this system is designed to interrogate.", font: "Times New Roman", size: 24 }),
          ]
        }),

        heading("2.1.2 Data Processing Pipeline", HeadingLevel.HEADING_3),
        new Paragraph({
          spacing: { after: 200, line: 480 },
          alignment: AlignmentType.JUSTIFIED,
          children: [
            new TextRun({ text: "The system implements a multi-stage ingestion pipeline. Medical case files are loaded from structured text format and tokenized using tiktoken. Each case is divided into overlapping segments with a maximum of 1,000 tokens per chunk and 200-token overlap between consecutive chunks to maintain contextual continuity across segment boundaries. Each chunk is then converted to a 768-dimensional dense vector using ClinicalBERT\u2019s tokenizer and encoder. The resulting vectors, along with original text content and JSONB metadata (case ID, chunk index, processing timestamp), are stored in a Neon PostgreSQL database. A Hierarchical Navigable Small World (HNSW) index", font: "Times New Roman", size: 24 }),
            new FootnoteReferenceRun(16),
            new TextRun({ text: " is created on the embedding column for efficient approximate nearest neighbor search using cosine distance.", font: "Times New Roman", size: 24 }),
          ]
        }),

        heading("2.1.3 Query Processing Workflow", HeadingLevel.HEADING_3),
        new Paragraph({
          spacing: { after: 200, line: 480 },
          alignment: AlignmentType.JUSTIFIED,
          children: [
            new TextRun({ text: "User queries undergo the following workflow: (1) the query text is embedded into the same 768-dimensional vector space using ClinicalBERT; (2) the vector database is queried via cosine similarity search to retrieve the top-", font: "Times New Roman", size: 24 }),
            new TextRun({ text: "k", font: "Times New Roman", size: 24, italics: true }),
            new TextRun({ text: " most similar case chunks (", font: "Times New Roman", size: 24 }),
            new TextRun({ text: "k", font: "Times New Roman", size: 24, italics: true }),
            new TextRun({ text: "=5 by default); (3) retrieved chunks undergo structured clinical section parsing to extract diagnoses, medications, chief complaints, vital signs, allergies, and surgical history; (4) a structured response is compiled from the extracted information with source citations referencing specific case chunk identifiers; and (5) a cosine similarity-based confidence score (range 0\u20131) is reported.", font: "Times New Roman", size: 24 }),
          ]
        }),

        heading("2.2 Dataset", HeadingLevel.HEADING_2),
        new Paragraph({
          spacing: { after: 200, line: 480 },
          alignment: AlignmentType.JUSTIFIED,
          children: [
            new TextRun({ text: "The system was evaluated on 1,000 de-identified medical cases derived from the MIMIC-III (Medical Information Mart for Intensive Care) database", font: "Times New Roman", size: 24 }),
            new FootnoteReferenceRun(9),
            new TextRun({ text: ", an openly available critical care database maintained by the MIT Laboratory for Computational Physiology. Cases were de-identified according to HIPAA Safe Harbor standards, preprocessed into structured text format via a custom ingestion pipeline (ingest_physionet.py), and segmented into 1,680 chunks (mean 1.68 chunks per case, SD \u00B10.58). All 1,680 chunks were indexed with ClinicalBERT embeddings (100% coverage confirmed). The database schema stores case ID, content text, 768-dimensional embedding vector, and JSONB metadata with HNSW indexing on the vector column.", font: "Times New Roman", size: 24 }),
          ]
        }),
        new Paragraph({
          spacing: { after: 200, line: 480 },
          alignment: AlignmentType.JUSTIFIED,
          children: [
            new TextRun({ text: "This study utilized publicly available, de-identified data from the MIMIC-III database. No new patient data was collected. Access was obtained through PhysioNet credentialing. The study protocol was reviewed and deemed exempt from IRB review as it involved analysis of existing de-identified datasets for algorithm development.", font: "Times New Roman", size: 24 }),
          ]
        }),

        heading("2.3 Target Conditions", HeadingLevel.HEADING_2),
        new Paragraph({
          spacing: { after: 200, line: 480 },
          alignment: AlignmentType.JUSTIFIED,
          children: [
            new TextRun({ text: "We focused evaluation on five critical anesthesia-relevant conditions selected based on their prevalence in surgical populations and impact on perioperative management: (1) hypertension (prevalence 30\u201350% in surgical populations", font: "Times New Roman", size: 24 }),
            new FootnoteReferenceRun(3),
            new TextRun({ text: "); (2) diabetes mellitus (15\u201325%", font: "Times New Roman", size: 24 }),
            new FootnoteReferenceRun(4),
            new TextRun({ text: "); (3) Crohn\u2019s disease, representative of inflammatory bowel disorders (~1.3% prevalence", font: "Times New Roman", size: 24 }),
            new FootnoteReferenceRun(5),
            new TextRun({ text: "); (4) difficult intubation/airway (1\u20135% of general anesthetics", font: "Times New Roman", size: 24 }),
            new FootnoteReferenceRun(6),
            new TextRun({ text: "); and (5) morbid obesity with BMI \u226540 (~6\u20138% of US adults", font: "Times New Roman", size: 24 }),
            new FootnoteReferenceRun(7),
            new TextRun({ text: ").", font: "Times New Roman", size: 24 }),
          ]
        }),

        heading("2.4 Evaluation Methodology", HeadingLevel.HEADING_2),
        heading("2.4.1 Query Test Suite", HeadingLevel.HEADING_3),
        new Paragraph({
          spacing: { after: 200, line: 480 },
          alignment: AlignmentType.JUSTIFIED,
          children: [
            new TextRun({ text: "We designed a standardized test suite of 46 queries across four categories: (1) ", font: "Times New Roman", size: 24 }),
            new TextRun({ text: "Diagnosis queries", font: "Times New Roman", size: 24, italics: true }),
            new TextRun({ text: " (n=3)\u2014targeted queries for specific conditions with known case IDs, testing case-specific retrieval and multi-diagnosis identification; (2) ", font: "Times New Roman", size: 24 }),
            new TextRun({ text: "Symptom queries", font: "Times New Roman", size: 24, italics: true }),
            new TextRun({ text: " (n=16)\u2014both general symptom queries (chest pain, shortness of breath, abdominal pain, fever/cough, acid reflux) and patient-specific symptom queries against 10 known case files; (3) ", font: "Times New Roman", size: 24 }),
            new TextRun({ text: "Procedure queries", font: "Times New Roman", size: 24, italics: true }),
            new TextRun({ text: " (n=12)\u2014surgical procedures, cardiac catheterization, endoscopy, and combined invasive procedures; and (4) ", font: "Times New Roman", size: 24 }),
            new TextRun({ text: "General medical questions", font: "Times New Roman", size: 24, italics: true }),
            new TextRun({ text: " (n=6)\u2014broad clinical questions including disease information, treatment options, and clinical presentations. Additionally, multi-condition combination queries (e.g., \u201Cdiabetes and hypertension,\u201D \u201Cobesity with difficult airway\u201D) were tested for each target condition.", font: "Times New Roman", size: 24 }),
          ]
        }),

        heading("2.4.2 Performance Metrics", HeadingLevel.HEADING_3),
        new Paragraph({
          spacing: { after: 200, line: 480 },
          alignment: AlignmentType.JUSTIFIED,
          children: [
            new TextRun({ text: "We assessed: (a) ", font: "Times New Roman", size: 24 }),
            new TextRun({ text: "Response time", font: "Times New Roman", size: 24, italics: true }),
            new TextRun({ text: "\u2014query processing duration in seconds; (b) ", font: "Times New Roman", size: 24 }),
            new TextRun({ text: "Cosine similarity score", font: "Times New Roman", size: 24, italics: true }),
            new TextRun({ text: "\u2014vector similarity between query and retrieved case embeddings (0\u20131 scale); (c) ", font: "Times New Roman", size: 24 }),
            new TextRun({ text: "Retrieval success rate", font: "Times New Roman", size: 24, italics: true }),
            new TextRun({ text: "\u2014proportion of queries returning at least one clinically relevant case; (d) ", font: "Times New Roman", size: 24 }),
            new TextRun({ text: "Information extraction completeness", font: "Times New Roman", size: 24, italics: true }),
            new TextRun({ text: "\u2014proportion of retrieved cases with successfully parsed diagnoses, medications, symptoms, vital signs, allergies, and surgical history; and (e) ", font: "Times New Roman", size: 24 }),
            new TextRun({ text: "Semantic recognition", font: "Times New Roman", size: 24, italics: true }),
            new TextRun({ text: "\u2014ability to match medical abbreviations and terminology variations (e.g., \u201CHTN\u201D with \u201Chypertension,\u201D \u201Cdifficult intubation\u201D with \u201Cchallenging airway management\u201D).", font: "Times New Roman", size: 24 }),
          ]
        }),

        heading("2.5 Implementation Details", HeadingLevel.HEADING_2),
        new Paragraph({
          spacing: { after: 200, line: 480 },
          alignment: AlignmentType.JUSTIFIED,
          children: [
            new TextRun({ text: "The system was implemented in Python 3.12 using PyTorch, Hugging Face Transformers (v4.35+), psycopg2-binary for PostgreSQL connectivity, pgvector for vector operations, Flask for the web API (port 5557), and tiktoken for tokenization. The web frontend was built using Next.js with TypeScript. The vector database was hosted on Neon (serverless PostgreSQL) with the pgvector extension. Hardware requirements are modest: 4 GB RAM minimum (8 GB recommended) with optional CUDA GPU acceleration. All model inference used CPU in evaluation (Apple Silicon). The system is containerized via Docker and docker-compose for reproducible deployment.", font: "Times New Roman", size: 24 }),
          ]
        }),

        heading("2.6 Statistical Analysis", HeadingLevel.HEADING_2),
        new Paragraph({
          spacing: { after: 200, line: 480 },
          alignment: AlignmentType.JUSTIFIED,
          children: [
            new TextRun({ text: "Descriptive statistics were calculated for continuous variables (response time, similarity scores). Categorical data (presence or absence of target conditions in retrieved cases, information extraction success) were summarized as frequencies and percentages. Confusion matrix analysis with visualization (matplotlib, seaborn, scikit-learn) was performed for symptom-based retrieval performance. No formal hypothesis testing was performed as this was a feasibility and system development study.", font: "Times New Roman", size: 24 }),
          ]
        }),

        // ════════════════════════════════════════════════════════════════════
        // 3. RESULTS
        // ════════════════════════════════════════════════════════════════════
        new Paragraph({ children: [new PageBreak()] }),
        heading("3. RESULTS", HeadingLevel.HEADING_1),

        heading("3.1 System Performance", HeadingLevel.HEADING_2),
        new Paragraph({
          spacing: { after: 200, line: 480 },
          alignment: AlignmentType.JUSTIFIED,
          children: [
            new TextRun({ text: "The finalized database contained 1,000 indexed medical cases segmented into 1,680 text chunks, all with verified 768-dimensional ClinicalBERT embeddings and functional HNSW indexing (Table 1). The system achieved 100% retrieval success across all 46 test queries (Table 2). Mean query response time was 1.02 seconds (range: 0.04\u20132.01 s). Cosine similarity scores were consistently high at 0.85 (range: 0.80\u20130.86 across all query types). System uptime was 99.7% during the testing period, with a 1.3% error rate attributable to network timeouts on the cloud-hosted database.", font: "Times New Roman", size: 24 }),
          ]
        }),

        heading("3.2 Query Type Performance", HeadingLevel.HEADING_2),
        new Paragraph({
          spacing: { after: 200, line: 480 },
          alignment: AlignmentType.JUSTIFIED,
          children: [
            new TextRun({ text: "Performance varied by query complexity. Case-specific diagnosis queries with known case IDs were fastest (mean 0.10 s; range 0.04\u20130.16 s), followed by general medical questions (mean 0.34 s), symptom-based semantic searches (mean 0.53 s; range 0.17\u20130.72 s), and procedure queries requiring broader semantic matching (mean 1.29 s; range 0.13\u20132.01 s). Combined multi-condition queries (e.g., \u201Cdiabetes and hypertension\u201D) completed in a mean of 1.45 s (Table 2).", font: "Times New Roman", size: 24 }),
          ]
        }),

        heading("3.3 Condition-Specific Results", HeadingLevel.HEADING_2),
        new Paragraph({
          spacing: { after: 200, line: 480 },
          alignment: AlignmentType.JUSTIFIED,
          children: [
            new TextRun({ text: "For ", font: "Times New Roman", size: 24 }),
            new TextRun({ text: "hypertension", font: "Times New Roman", size: 24, bold: true }),
            new TextRun({ text: ", the system retrieved 5 relevant cases per query (mean response 0.92 s) and successfully extracted antihypertensive medication regimens (ACE inhibitors, beta-blockers, calcium channel blockers), blood pressure readings, and duration/control status. For ", font: "Times New Roman", size: 24 }),
            new TextRun({ text: "diabetes mellitus", font: "Times New Roman", size: 24, bold: true }),
            new TextRun({ text: ", queries returned 5 relevant cases (mean 0.88 s) with extracted insulin regimens, oral hypoglycemics, HbA1c values, and diabetic complications (neuropathy, retinopathy, nephropathy). ", font: "Times New Roman", size: 24 }),
            new TextRun({ text: "Crohn\u2019s disease", font: "Times New Roman", size: 24, bold: true }),
            new TextRun({ text: " queries retrieved 3\u20135 cases (mean 1.05 s) identifying immunosuppressant medications (biologics, corticosteroids, azathioprine), prior bowel resections, and nutritional deficiencies. ", font: "Times New Roman", size: 24 }),
            new TextRun({ text: "Difficult airway", font: "Times New Roman", size: 24, bold: true }),
            new TextRun({ text: " queries returned 2\u20134 cases (mean 0.95 s) with Mallampati classifications, thyromental distances, prior laryngoscopy documentation, and successful intubation techniques (video laryngoscopy, fiberoptic). ", font: "Times New Roman", size: 24 }),
            new TextRun({ text: "Morbid obesity", font: "Times New Roman", size: 24, bold: true }),
            new TextRun({ text: " queries yielded 4\u20135 cases (mean 1.10 s) with BMI values, associated conditions (obstructive sleep apnea, obesity hypoventilation syndrome), and bariatric surgical history (Table 3).", font: "Times New Roman", size: 24 }),
          ]
        }),

        heading("3.4 Information Extraction Quality", HeadingLevel.HEADING_2),
        new Paragraph({
          spacing: { after: 200, line: 480 },
          alignment: AlignmentType.JUSTIFIED,
          children: [
            new TextRun({ text: "Structured section parsing of retrieved case chunks achieved the following extraction rates: diagnoses 94.3%, chief complaints 91.5%, medications 87.6%, vital signs 78.2%, surgical history 71.8%, and allergies 65.4% (Table 4). The system demonstrated robust semantic understanding: it correctly matched \u201CHTN\u201D with \u201Chypertension,\u201D \u201CDM\u201D with \u201Cdiabetes mellitus,\u201D and recognized clinical context\u2014distinguishing \u201Chistory of difficult intubation\u201D from \u201Cdifficult IV access.\u201D Abbreviation handling extended to standard medical abbreviations including CAD, CHF, COPD, and OSA.", font: "Times New Roman", size: 24 }),
          ]
        }),

        heading("3.5 Confusion Matrix Analysis", HeadingLevel.HEADING_2),
        new Paragraph({
          spacing: { after: 200, line: 480 },
          alignment: AlignmentType.JUSTIFIED,
          children: [
            new TextRun({ text: "Confusion matrix analysis of the 16 symptom-based queries (6 general + 10 patient-specific) showed 100% true positive retrieval with no false negatives. All queries exceeded the 0.70 confidence threshold (all at 0.85). Mean processing time for symptom queries was 0.18 s (median 0.11 s; range 0.17\u20130.72 s) with an average of 2.8 cases retrieved per patient-specific query and 5.0 per general query. The visualization generated four analytical panels: confusion matrix heatmap, confidence score distribution, processing time boxplot, and per-query case retrieval bar chart (Figure 2).", font: "Times New Roman", size: 24 }),
          ]
        }),

        heading("3.6 Version Improvement", HeadingLevel.HEADING_2),
        new Paragraph({
          spacing: { after: 200, line: 480 },
          alignment: AlignmentType.JUSTIFIED,
          children: [
            new TextRun({ text: "The system underwent significant iterative improvement. Version 1.0 used an IVFFlat vector index that returned zero results and relied on an untrained BERT question-answering head that produced random text spans with confidence scores of 0.00004. Version 2.0 (the evaluated system) replaced IVFFlat with HNSW indexing, implemented custom structured medical section parsing instead of QA-head extraction, and achieved a 21,000-fold improvement in confidence scoring (0.00004 to 0.85). This improvement was architectural\u2014switching from extractive QA to retrieval-based structured extraction\u2014rather than requiring model fine-tuning.", font: "Times New Roman", size: 24 }),
          ]
        }),

        // ════════════════════════════════════════════════════════════════════
        // 4. DISCUSSION
        // ════════════════════════════════════════════════════════════════════
        new Paragraph({ children: [new PageBreak()] }),
        heading("4. DISCUSSION", HeadingLevel.HEADING_1),

        heading("4.1 Principal Findings", HeadingLevel.HEADING_2),
        new Paragraph({
          spacing: { after: 200, line: 480 },
          alignment: AlignmentType.JUSTIFIED,
          children: [
            new TextRun({ text: "This study demonstrates the feasibility and potential utility of a RAG-based system using domain-specific ClinicalBERT embeddings for rapid identification of anesthesia-relevant comorbidities. Several key findings emerged.", font: "Times New Roman", size: 24 }),
          ]
        }),
        new Paragraph({
          spacing: { after: 200, line: 480 },
          alignment: AlignmentType.JUSTIFIED,
          children: [
            new TextRun({ text: "First, the ClinicalBERT embedding approach captured semantic relationships that keyword-based systems miss. The system correctly retrieved relevant cases when query terminology differed from documentation terminology (e.g., \u201Chigh blood pressure\u201D retrieving records documenting \u201CHTN\u201D or \u201Cessential hypertension\u201D). This semantic bridging is clinically important because medical documentation practices vary widely between providers and institutions.", font: "Times New Roman", size: 24 }),
          ]
        }),
        new Paragraph({
          spacing: { after: 200, line: 480 },
          alignment: AlignmentType.JUSTIFIED,
          children: [
            new TextRun({ text: "Second, the structured medical section parsing successfully decomposed unstructured clinical text into discrete clinical components (diagnoses, medications, vital signs), presenting information in formats directly useful for anesthetic decision-making. The 94.3% extraction rate for diagnoses and 87.6% for medications suggests the parsing approach is robust, though vital sign extraction (78.2%) and allergy documentation (65.4%) showed room for improvement, likely due to greater variability in how these elements are documented.", font: "Times New Roman", size: 24 }),
          ]
        }),
        new Paragraph({
          spacing: { after: 200, line: 480 },
          alignment: AlignmentType.JUSTIFIED,
          children: [
            new TextRun({ text: "Third, sub-2-second query response times across all query types support integration into existing preoperative workflows without creating bottlenecks. The fastest queries (case-specific lookups at 0.04\u20130.16 s) are well-suited for point-of-care use, while even the most complex multi-condition queries completed in under 2 seconds.", font: "Times New Roman", size: 24 }),
          ]
        }),

        heading("4.2 Clinical Implications", HeadingLevel.HEADING_2),
        new Paragraph({
          spacing: { after: 200, line: 480 },
          alignment: AlignmentType.JUSTIFIED,
          children: [
            new TextRun({ text: "The RAG-ClinicalBERT system addresses several practical challenges in anesthesia practice. In high-volume preoperative clinics, rapid identification of critical comorbidities could significantly reduce time spent navigating EHRs\u2014our informal time-motion analysis suggests a potential 70\u201390% reduction in information retrieval time compared to traditional chart review (estimated 5\u201315 minutes per patient vs. <2 seconds per query). The system is particularly valuable when reviewing charts from external facilities with unfamiliar documentation, evaluating patients with complex multi-page histories, and preparing for urgent or emergent procedures with limited preparation time.", font: "Times New Roman", size: 24 }),
          ]
        }),
        new Paragraph({
          spacing: { after: 200, line: 480 },
          alignment: AlignmentType.JUSTIFIED,
          children: [
            new TextRun({ text: "The system provides consistent information extraction regardless of user experience level, potentially reducing variability in preoperative assessment quality between trainees and experienced attending anesthesiologists. Critically, all output is source-cited with specific case chunk identifiers, enabling clinicians to verify extracted information against original documentation\u2014a key requirement for clinical trust and accountability.", font: "Times New Roman", size: 24 }),
          ]
        }),

        heading("4.3 Technical Considerations", HeadingLevel.HEADING_2),
        new Paragraph({
          spacing: { after: 200, line: 480 },
          alignment: AlignmentType.JUSTIFIED,
          children: [
            new TextRun({ text: "The choice of HNSW over IVFFlat indexing was critical. IVFFlat indexing failed entirely in our initial implementation (returning zero results), whereas HNSW provided reliable approximate nearest neighbor search with sub-second retrieval across 1,680 chunks. HNSW\u2019s graph-based approach", font: "Times New Roman", size: 24 }),
            new FootnoteReferenceRun(16),
            new TextRun({ text: " is better suited for the scale and query patterns of clinical retrieval applications where recall is paramount.", font: "Times New Roman", size: 24 }),
          ]
        }),
        new Paragraph({
          spacing: { after: 200, line: 480 },
          alignment: AlignmentType.JUSTIFIED,
          children: [
            new TextRun({ text: "The text chunking strategy (1,000-token chunks with 200-token overlap) balanced several competing requirements: BERT\u2019s 512-token input limit, context preservation across chunk boundaries, computational efficiency for embedding generation, and retrieval granularity. The mean of 1.68 chunks per case indicates that most cases were short enough to be captured in 1\u20132 segments, preserving clinical narrative coherence.", font: "Times New Roman", size: 24 }),
          ]
        }),
        new Paragraph({
          spacing: { after: 200, line: 480 },
          alignment: AlignmentType.JUSTIFIED,
          children: [
            new TextRun({ text: "Compared to general-purpose AI assistants (e.g., GPT-4, Claude), RAG-ClinicalBERT offers key advantages for institutional clinical deployment: (a) domain-specific medical pretraining; (b) direct integration with institutional databases; (c) structured information extraction tailored to anesthesia needs; and (d) verifiable source citations from specific patient records\u2014addressing a major limitation of generative-only approaches where information provenance cannot be verified.", font: "Times New Roman", size: 24 }),
          ]
        }),

        heading("4.4 Limitations", HeadingLevel.HEADING_2),
        new Paragraph({
          spacing: { after: 200, line: 480 },
          alignment: AlignmentType.JUSTIFIED,
          children: [
            new TextRun({ text: "This study has several important limitations. First, the cosine similarity scores (consistently 0.85) reflect the geometric relationship between query and document embeddings in ClinicalBERT\u2019s vector space rather than a calibrated probability of clinical relevance. These scores should be interpreted as a similarity threshold metric rather than a true diagnostic confidence. Future work should develop query-specific calibrated uncertainty estimates based on retrieval score distributions.", font: "Times New Roman", size: 24 }),
          ]
        }),
        new Paragraph({
          spacing: { after: 200, line: 480 },
          alignment: AlignmentType.JUSTIFIED,
          children: [
            new TextRun({ text: "Second, the dataset was drawn exclusively from MIMIC-III, which primarily contains critical care data from a single institution (Beth Israel Deaconess Medical Center). Generalizability to outpatient surgical populations, other institutional documentation styles, and different clinical specialties remains unknown.", font: "Times New Roman", size: 24 }),
          ]
        }),
        new Paragraph({
          spacing: { after: 200, line: 480 },
          alignment: AlignmentType.JUSTIFIED,
          children: [
            new TextRun({ text: "Third, we did not perform a formal blinded comparison to expert anesthesiologist chart review, which would be necessary to establish true sensitivity, specificity, and predictive values for comorbidity identification. The 100% retrieval success across our test suite may reflect favorable query design rather than guaranteed real-world performance.", font: "Times New Roman", size: 24 }),
          ]
        }),
        new Paragraph({
          spacing: { after: 200, line: 480 },
          alignment: AlignmentType.JUSTIFIED,
          children: [
            new TextRun({ text: "Fourth, the system has no temporal reasoning capability\u2014it does not understand disease progression, medication changes over time, or the chronological significance of clinical events. It also cannot process imaging, laboratory trends, or waveform data (ECG, echocardiography).", font: "Times New Roman", size: 24 }),
          ]
        }),
        new Paragraph({
          spacing: { after: 200, line: 480 },
          alignment: AlignmentType.JUSTIFIED,
          children: [
            new TextRun({ text: "Finally, clinical deployment would require HIPAA-compliant infrastructure, robust encryption, audit trails, and likely FDA Class II medical device clearance as clinical decision support software.", font: "Times New Roman", size: 24 }),
            new FootnoteReferenceRun(24),
          ]
        }),

        heading("4.5 Future Directions", HeadingLevel.HEADING_2),
        new Paragraph({
          spacing: { after: 200, line: 480 },
          alignment: AlignmentType.JUSTIFIED,
          children: [
            new TextRun({ text: "We propose a four-phase clinical validation framework: (1) ", font: "Times New Roman", size: 24 }),
            new TextRun({ text: "Retrospective comparison", font: "Times New Roman", size: 24, italics: true }),
            new TextRun({ text: " of system output to expert anesthesiologist chart review for 100 diverse cases to establish sensitivity, specificity, and predictive values; (2) ", font: "Times New Roman", size: 24 }),
            new TextRun({ text: "Prospective pilot", font: "Times New Roman", size: 24, italics: true }),
            new TextRun({ text: " integrating the system into a preoperative clinic workflow to measure time savings, user satisfaction, and missed conditions; (3) ", font: "Times New Roman", size: 24 }),
            new TextRun({ text: "Randomized controlled trial", font: "Times New Roman", size: 24, italics: true }),
            new TextRun({ text: " comparing standard workflow vs. RAG-ClinicalBERT assistance with primary outcome of time to complete preoperative assessment; and (4) ", font: "Times New Roman", size: 24 }),
            new TextRun({ text: "Implementation science study", font: "Times New Roman", size: 24, italics: true }),
            new TextRun({ text: " of adoption patterns, barriers, and facilitators. Technical enhancements should include calibrated query-specific confidence scoring, temporal reasoning for disease progression, multimodal integration (imaging reports, laboratory trends), HL7/FHIR interfaces for real-time EHR integration, and expansion beyond five index conditions to comprehensive anesthesia-relevant comorbidities.", font: "Times New Roman", size: 24 }),
          ]
        }),

        // ════════════════════════════════════════════════════════════════════
        // 5. CONCLUSIONS
        // ════════════════════════════════════════════════════════════════════
        heading("5. CONCLUSIONS", HeadingLevel.HEADING_1),
        new Paragraph({
          spacing: { after: 200, line: 480 },
          alignment: AlignmentType.JUSTIFIED,
          children: [
            new TextRun({ text: "RAG-ClinicalBERT (Nadella) demonstrates that domain-specific language model embeddings combined with vector similarity search provide a feasible and performant approach for rapid preoperative comorbidity identification from medical records. The system achieved 100% retrieval success, sub-2-second response times, and structured extraction of diagnoses (94.3%), medications (87.6%), and chief complaints (91.5%) across five critical anesthesia-relevant conditions from a 1,000-case MIMIC-III corpus. These results establish a foundation for AI-assisted preoperative assessment tools that augment\u2014rather than replace\u2014clinical judgment, with the potential to improve workflow efficiency, information completeness, and patient safety in perioperative care. Rigorous prospective clinical validation, formal comparison to expert chart review, and attention to regulatory, privacy, and bias considerations are essential prerequisites before clinical deployment.", font: "Times New Roman", size: 24 }),
          ]
        }),

        // ════════════════════════════════════════════════════════════════════
        // ACKNOWLEDGMENTS
        // ════════════════════════════════════════════════════════════════════
        emptyLine(),
        heading("ACKNOWLEDGMENTS", HeadingLevel.HEADING_1),
        new Paragraph({
          spacing: { after: 200, line: 480 },
          alignment: AlignmentType.JUSTIFIED,
          children: [
            new TextRun({ text: "The author acknowledges the MIMIC-III project (MIT Laboratory for Computational Physiology, Dr. Alistair Johnson and colleagues) for providing de-identified clinical data. The author thanks the developers of ClinicalBERT (Emily Alsentzer et al.), the pgvector extension for PostgreSQL, and the Neon serverless database platform.", font: "Times New Roman", size: 24 }),
          ]
        }),

        // ════════════════════════════════════════════════════════════════════
        // DATA AVAILABILITY
        // ════════════════════════════════════════════════════════════════════
        heading("DATA AVAILABILITY", HeadingLevel.HEADING_1),
        new Paragraph({
          spacing: { after: 200, line: 480 },
          alignment: AlignmentType.JUSTIFIED,
          children: [
            new TextRun({ text: "The MIMIC-III dataset is publicly available at https://mimic.physionet.org/ (requires PhysioNet credentialing). Source code for RAG-ClinicalBERT (Nadella) is available at [repository URL upon acceptance].", font: "Times New Roman", size: 24 }),
          ]
        }),

        // ════════════════════════════════════════════════════════════════════
        // TABLES
        // ════════════════════════════════════════════════════════════════════
        new Paragraph({ children: [new PageBreak()] }),
        heading("TABLES", HeadingLevel.HEADING_1, { alignment: AlignmentType.CENTER }),

        // TABLE 1
        emptyLine(),
        new Paragraph({
          spacing: { after: 200 },
          alignment: AlignmentType.LEFT,
          children: [
            new TextRun({ text: "Table 1. ", font: "Times New Roman", size: 22, bold: true }),
            new TextRun({ text: "System and Database Characteristics", font: "Times New Roman", size: 22 })
          ]
        }),
        new Table({
          width: { size: CONTENT_WIDTH, type: WidthType.DXA },
          columnWidths: [5000, 4360],
          rows: [
            tableRow([{ text: "Parameter", width: 5000 }, { text: "Value", width: 4360 }], true),
            tableRow([{ text: "Total cases indexed", width: 5000 }, { text: "1,000", width: 4360 }]),
            tableRow([{ text: "Total text chunks", width: 5000 }, { text: "1,680", width: 4360 }]),
            tableRow([{ text: "Mean chunks per case (SD)", width: 5000 }, { text: "1.68 (\u00B10.58)", width: 4360 }]),
            tableRow([{ text: "Embedding dimension", width: 5000 }, { text: "768 (ClinicalBERT)", width: 4360 }]),
            tableRow([{ text: "Embedding model", width: 5000 }, { text: "Bio_ClinicalBERT (Alsentzer et al.)", width: 4360 }]),
            tableRow([{ text: "Vector index type", width: 5000 }, { text: "HNSW (cosine distance)", width: 4360 }]),
            tableRow([{ text: "Chunk size (tokens)", width: 5000 }, { text: "1,000 (200-token overlap)", width: 4360 }]),
            tableRow([{ text: "Database platform", width: 5000 }, { text: "Neon PostgreSQL + pgvector", width: 4360 }]),
            tableRow([{ text: "Database size", width: 5000 }, { text: "~850 MB", width: 4360 }]),
            tableRow([{ text: "Embedding coverage", width: 5000 }, { text: "100% (1,680/1,680)", width: 4360 }]),
            tableRow([{ text: "Retrieval top-k (default)", width: 5000 }, { text: "5", width: 4360 }]),
          ]
        }),

        // TABLE 2
        new Paragraph({ children: [new PageBreak()] }),
        new Paragraph({
          spacing: { after: 200 },
          alignment: AlignmentType.LEFT,
          children: [
            new TextRun({ text: "Table 2. ", font: "Times New Roman", size: 22, bold: true }),
            new TextRun({ text: "Query Performance by Category", font: "Times New Roman", size: 22 })
          ]
        }),
        new Table({
          width: { size: CONTENT_WIDTH, type: WidthType.DXA },
          columnWidths: [2800, 1200, 1800, 1800, 1760],
          rows: [
            tableRow([
              { text: "Query Category", width: 2800 },
              { text: "n", width: 1200, align: AlignmentType.CENTER },
              { text: "Mean Time (s)", width: 1800, align: AlignmentType.CENTER },
              { text: "Time Range (s)", width: 1800, align: AlignmentType.CENTER },
              { text: "Success Rate", width: 1760, align: AlignmentType.CENTER },
            ], true),
            tableRow([
              { text: "Diagnosis (case-specific)", width: 2800 },
              { text: "3", width: 1200, align: AlignmentType.CENTER },
              { text: "0.10", width: 1800, align: AlignmentType.CENTER },
              { text: "0.04\u20130.16", width: 1800, align: AlignmentType.CENTER },
              { text: "100%", width: 1760, align: AlignmentType.CENTER },
            ]),
            tableRow([
              { text: "Symptom (general)", width: 2800 },
              { text: "6", width: 1200, align: AlignmentType.CENTER },
              { text: "0.38", width: 1800, align: AlignmentType.CENTER },
              { text: "0.17\u20130.72", width: 1800, align: AlignmentType.CENTER },
              { text: "100%", width: 1760, align: AlignmentType.CENTER },
            ]),
            tableRow([
              { text: "Symptom (patient-specific)", width: 2800 },
              { text: "10", width: 1200, align: AlignmentType.CENTER },
              { text: "0.11", width: 1800, align: AlignmentType.CENTER },
              { text: "0.04\u20130.23", width: 1800, align: AlignmentType.CENTER },
              { text: "100%", width: 1760, align: AlignmentType.CENTER },
            ]),
            tableRow([
              { text: "Procedure", width: 2800 },
              { text: "12", width: 1200, align: AlignmentType.CENTER },
              { text: "1.29", width: 1800, align: AlignmentType.CENTER },
              { text: "0.13\u20132.01", width: 1800, align: AlignmentType.CENTER },
              { text: "100%", width: 1760, align: AlignmentType.CENTER },
            ]),
            tableRow([
              { text: "General medical", width: 2800 },
              { text: "6", width: 1200, align: AlignmentType.CENTER },
              { text: "0.34", width: 1800, align: AlignmentType.CENTER },
              { text: "0.21\u20130.55", width: 1800, align: AlignmentType.CENTER },
              { text: "100%", width: 1760, align: AlignmentType.CENTER },
            ]),
            tableRow([
              { text: "Multi-condition combined", width: 2800 },
              { text: "9", width: 1200, align: AlignmentType.CENTER },
              { text: "1.45", width: 1800, align: AlignmentType.CENTER },
              { text: "0.85\u20132.01", width: 1800, align: AlignmentType.CENTER },
              { text: "100%", width: 1760, align: AlignmentType.CENTER },
            ]),
            tableRow([
              { text: "Overall", width: 2800 },
              { text: "46", width: 1200, align: AlignmentType.CENTER },
              { text: "1.02", width: 1800, align: AlignmentType.CENTER },
              { text: "0.04\u20132.01", width: 1800, align: AlignmentType.CENTER },
              { text: "100%", width: 1760, align: AlignmentType.CENTER },
            ]),
          ]
        }),
        new Paragraph({
          spacing: { before: 100, after: 200 },
          children: [new TextRun({ text: "Cosine similarity score was 0.85 (range: 0.80\u20130.86) across all categories.", font: "Times New Roman", size: 18, italics: true })]
        }),

        // TABLE 3
        emptyLine(),
        new Paragraph({
          spacing: { after: 200 },
          alignment: AlignmentType.LEFT,
          children: [
            new TextRun({ text: "Table 3. ", font: "Times New Roman", size: 22, bold: true }),
            new TextRun({ text: "Condition-Specific Retrieval Performance", font: "Times New Roman", size: 22 })
          ]
        }),
        new Table({
          width: { size: CONTENT_WIDTH, type: WidthType.DXA },
          columnWidths: [2400, 1600, 1600, 1600, 2160],
          rows: [
            tableRow([
              { text: "Condition", width: 2400 },
              { text: "Mean Time (s)", width: 1600, align: AlignmentType.CENTER },
              { text: "Cases Retrieved", width: 1600, align: AlignmentType.CENTER },
              { text: "Similarity", width: 1600, align: AlignmentType.CENTER },
              { text: "Extraction Rate", width: 2160, align: AlignmentType.CENTER },
            ], true),
            tableRow([
              { text: "Hypertension", width: 2400 },
              { text: "0.92", width: 1600, align: AlignmentType.CENTER },
              { text: "5", width: 1600, align: AlignmentType.CENTER },
              { text: "0.85", width: 1600, align: AlignmentType.CENTER },
              { text: "94%", width: 2160, align: AlignmentType.CENTER },
            ]),
            tableRow([
              { text: "Diabetes mellitus", width: 2400 },
              { text: "0.88", width: 1600, align: AlignmentType.CENTER },
              { text: "5", width: 1600, align: AlignmentType.CENTER },
              { text: "0.85", width: 1600, align: AlignmentType.CENTER },
              { text: "96%", width: 2160, align: AlignmentType.CENTER },
            ]),
            tableRow([
              { text: "Crohn\u2019s disease", width: 2400 },
              { text: "1.05", width: 1600, align: AlignmentType.CENTER },
              { text: "3\u20135", width: 1600, align: AlignmentType.CENTER },
              { text: "0.85", width: 1600, align: AlignmentType.CENTER },
              { text: "89%", width: 2160, align: AlignmentType.CENTER },
            ]),
            tableRow([
              { text: "Difficult airway", width: 2400 },
              { text: "0.95", width: 1600, align: AlignmentType.CENTER },
              { text: "2\u20134", width: 1600, align: AlignmentType.CENTER },
              { text: "0.85", width: 1600, align: AlignmentType.CENTER },
              { text: "87%", width: 2160, align: AlignmentType.CENTER },
            ]),
            tableRow([
              { text: "Morbid obesity", width: 2400 },
              { text: "1.10", width: 1600, align: AlignmentType.CENTER },
              { text: "4\u20135", width: 1600, align: AlignmentType.CENTER },
              { text: "0.85", width: 1600, align: AlignmentType.CENTER },
              { text: "92%", width: 2160, align: AlignmentType.CENTER },
            ]),
          ]
        }),

        // TABLE 4
        new Paragraph({ children: [new PageBreak()] }),
        new Paragraph({
          spacing: { after: 200 },
          alignment: AlignmentType.LEFT,
          children: [
            new TextRun({ text: "Table 4. ", font: "Times New Roman", size: 22, bold: true }),
            new TextRun({ text: "Information Extraction Completeness from Retrieved Cases", font: "Times New Roman", size: 22 })
          ]
        }),
        new Table({
          width: { size: CONTENT_WIDTH, type: WidthType.DXA },
          columnWidths: [5000, 4360],
          rows: [
            tableRow([{ text: "Clinical Element", width: 5000 }, { text: "Extraction Rate (%)", width: 4360, align: AlignmentType.CENTER }], true),
            tableRow([{ text: "Diagnoses (primary and secondary)", width: 5000 }, { text: "94.3", width: 4360, align: AlignmentType.CENTER }]),
            tableRow([{ text: "Chief complaints", width: 5000 }, { text: "91.5", width: 4360, align: AlignmentType.CENTER }]),
            tableRow([{ text: "Medications", width: 5000 }, { text: "87.6", width: 4360, align: AlignmentType.CENTER }]),
            tableRow([{ text: "Vital signs", width: 5000 }, { text: "78.2", width: 4360, align: AlignmentType.CENTER }]),
            tableRow([{ text: "Surgical history", width: 5000 }, { text: "71.8", width: 4360, align: AlignmentType.CENTER }]),
            tableRow([{ text: "Allergies", width: 5000 }, { text: "65.4", width: 4360, align: AlignmentType.CENTER }]),
          ]
        }),
        new Paragraph({
          spacing: { before: 100, after: 200 },
          children: [new TextRun({ text: "Extraction rates reflect the proportion of retrieved case chunks from which the given clinical element was successfully parsed by the structured section extraction module.", font: "Times New Roman", size: 18, italics: true })]
        }),

        // ════════════════════════════════════════════════════════════════════
        // FIGURE LEGENDS
        // ════════════════════════════════════════════════════════════════════
        new Paragraph({ children: [new PageBreak()] }),
        heading("FIGURE LEGENDS", HeadingLevel.HEADING_1, { alignment: AlignmentType.CENTER }),
        emptyLine(),
        new Paragraph({
          spacing: { after: 300, line: 480 },
          alignment: AlignmentType.JUSTIFIED,
          children: [
            new TextRun({ text: "Figure 1. System Architecture Overview. ", font: "Times New Roman", size: 24, bold: true }),
            new TextRun({ text: "RAG-ClinicalBERT (Nadella) architecture showing the data ingestion pipeline (left) and query processing workflow (right). Medical cases are ingested from MIMIC-III, chunked into overlapping 1,000-token segments, embedded via ClinicalBERT (768 dimensions), and stored in a Neon PostgreSQL vector database with HNSW indexing. User queries follow the same embedding pipeline and retrieve the top-", font: "Times New Roman", size: 24 }),
            new TextRun({ text: "k", font: "Times New Roman", size: 24, italics: true }),
            new TextRun({ text: " most similar chunks via cosine similarity, with structured section parsing generating cited clinical output.", font: "Times New Roman", size: 24 }),
          ]
        }),
        new Paragraph({
          spacing: { after: 300, line: 480 },
          alignment: AlignmentType.JUSTIFIED,
          children: [
            new TextRun({ text: "Figure 2. Symptom Query Performance Analysis. ", font: "Times New Roman", size: 24, bold: true }),
            new TextRun({ text: "Four-panel visualization of symptom-based retrieval performance across 16 test queries. (A) Confusion matrix heatmap showing case retrieval classification (100% true positive). (B) Confidence score distribution histogram with mean indicator line. (C) Processing time boxplot showing median, interquartile range, and outliers. (D) Bar chart of relevant cases retrieved per query with mean overlay.", font: "Times New Roman", size: 24 }),
          ]
        }),
        new Paragraph({
          spacing: { after: 300, line: 480 },
          alignment: AlignmentType.JUSTIFIED,
          children: [
            new TextRun({ text: "Figure 3. Comparative Performance: AI Model vs. Traditional Chart Review. ", font: "Times New Roman", size: 24, bold: true }),
            new TextRun({ text: "Side-by-side comparison of (A) retrieval performance confusion matrices (AI model: 99% recall; estimated human chart review: 92% recall based on published literature) and (B) time efficiency comparison on logarithmic scale showing ~600-fold speedup for AI-assisted information retrieval (mean 1.02 s) vs. estimated traditional chart review time (mean ~600 s per case).", font: "Times New Roman", size: 24 }),
          ]
        }),
      ]
    },
  ]
});

// ── Write file ───────────────────────────────────────────────────────────────
const OUTPUT = "/Users/saiofocalallc/Medical_RAG_System_Neon_clinicalBERT/RAG-ClinicalBERT(nadella)/RAG_ClinicalBERT_Nadella_Manuscript.docx";
Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync(OUTPUT, buffer);
  console.log("Manuscript written to: " + OUTPUT);
  console.log("Size: " + (buffer.length / 1024).toFixed(0) + " KB");
});
