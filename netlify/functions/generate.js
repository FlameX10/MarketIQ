const JSZip = require('jszip');
const fs = require('fs');
const path = require('path');

// Truncation limits map
const LENGTH_LIMITS = {
  type_segment_1: 30,
  type_segment_2: 35,
  type_segment_3: 50,
  tech_segment_1: 30,
  tech_segment_2: 30,
  tech_segment_3: 40,
  app_segment_1: 30,
  app_segment_2: 30,
  app_segment_3: 30,
  app_segment_4: 30,
  co1_name: 20,
  co2_name: 20,
  co3_name: 20,
  co4_name: 30,
  co5_name: 15,
  co6_name: 15,
  co7_name: 20,
  co8_name: 15,
  co9_name: 15,
  co10_name: 15,
  co1_segment_1_name: 50,
  co1_segment_2_name: 50,
  segment5_marketshare1: 30,
  segment5_marketshare2: 30,
  segment5_marketshare3: 30,
  segment5_marketshare4: 30,
  segment6_marketshare1: 30,
  segment6_marketshare2: 30,
  segment6_marketshare3: 30,
  segment6_marketshare4: 30,
  seg4_name: 30,
  seg4_sub1: 30,
  seg4_sub2: 30,
  seg4_sub3: 30,
  seg5_name: 30,
  seg5_sub1: 30,
  seg5_sub2: 30,
  seg5_sub3: 30,
  seg6_name: 30,
  seg6_sub1: 30,
  seg6_sub2: 30,
  seg6_sub3: 30,
  ch4_custom_subsection_4_1_title: 50,
};

function truncateText(text, maxLen) {
  if (!text) return text;
  const str = String(text).trim();
  if (str.length <= maxLen) return str;
  return str.slice(0, maxLen - 3).trim() + "...";
}

function extractCoreProductName(rawName) {
  const wordsToRemove = ["Global", "Market", "Segmentation", "Industry", "Analysis", "Overview"];
  let coreName = rawName;
  for (const word of wordsToRemove) {
    coreName = coreName.replace(new RegExp(`\\b${word}\\b`, 'gi'), '');
  }
  coreName = coreName.replace(/\s+/g, ' ').trim();
  if (!coreName) {
    const parts = rawName.split(/\s+/);
    coreName = parts.length > 1 ? parts.slice(0, 2).join(' ') : rawName;
  }
  return coreName.trim();
}

function sanitizeFilename(name) {
  const safe = name.replace(/[^a-zA-Z0-9\s\-_]/g, '_');
  return safe.trim().replace(/\s+/g, '_');
}

function getFallbackContent(marketName) {
  const core = extractCoreProductName(marketName);
  return {
    type_segment_1: `${core} Type 1`,
    type_segment_2: `${core} Type 2`,
    type_segment_3: `${core} Type 3`,
    tech_segment_1: `${core} Tech 1`,
    tech_segment_2: `${core} Tech 2`,
    tech_segment_3: `${core} Tech 3`,
    app_segment_1: `${core} App 1`,
    app_segment_2: `${core} App 2`,
    app_segment_3: `${core} App 3`,
    app_segment_4: `${core} App 4`,
    co1_name: "Featured Company",
    co2_name: "Competitor 2",
    co3_name: "Competitor 3",
    co4_name: "Competitor 4",
    co5_name: "Co5",
    co6_name: "Co6",
    co7_name: "Competitor 7",
    co8_name: "Co8",
    co9_name: "Co9",
    co10_name: "Co10",
    co1_segment_1_name: `${core} Segment 1`,
    co1_segment_2_name: `${core} Segment 2`,
    segment5_marketshare1: "Sub-Segment 1",
    segment5_marketshare2: "Sub-Segment 2",
    segment5_marketshare3: "Sub-Segment 3",
    segment6_marketshare1: "Sub-Segment 1",
    segment6_marketshare2: "Sub-Segment 2",
    segment6_marketshare3: "Sub-Segment 3",
    segment6_marketshare4: "Sub-Segment 4",
    seg4_name: `${core} Segment 4`,
    seg4_sub1: "Sub-Segment 1",
    seg4_sub2: "Sub-Segment 2",
    seg4_sub3: "Sub-Segment 3",
    seg5_name: `${core} Segment 5`,
    seg5_sub1: "Sub-Segment 1",
    seg5_sub2: "Sub-Segment 2",
    seg5_sub3: "Sub-Segment 3",
    seg6_name: `${core} Segment 6`,
    seg6_sub1: "Sub-Segment 1",
    seg6_sub2: "Sub-Segment 2",
    seg6_sub3: "Sub-Segment 3",
    ch4_custom_subsection_4_1_title: "Client Requirement 4.1",
  };
}

async function parseDocxBuffer(buffer) {
  const zip = await JSZip.loadAsync(buffer);
  const documentXml = await zip.file("word/document.xml").async("text");
  
  // Extract all text inside <w:t> elements
  const textMatches = documentXml.match(/<w:t[^>]*>(.*?)<\/w:t>/g) || [];
  const fullText = textMatches.map(m => m.replace(/<[^>]+>/g, '')).join(' ');

  let marketName = "Market Research Report";
  const nameMatch = fullText.match(/(?:Global\s+)?([A-Za-z0-9\s\-–]+?)\s+Market\s+Segmentation/i);
  if (nameMatch && nameMatch[1]) {
    marketName = extractCoreProductName(nameMatch[1]);
  } else {
    const titleMatch = fullText.match(/Global\s+([A-Za-z0-9\s\-–]+?)\s+Market/i);
    if (titleMatch && titleMatch[1]) {
      marketName = extractCoreProductName(titleMatch[1]);
    }
  }

  // Parse Segments
  const parsedSegments = [];
  const segmentLines = fullText.match(/\d+\.\s*([A-Za-z0-9\s\-]+):\s*([^.\n]+)/g) || [];
  for (const line of segmentLines) {
    const parts = line.split(':');
    if (parts.length >= 2) {
      const segName = parts[0].replace(/^\d+\.\s*/, '').trim();
      const subs = parts[1].split(',').map(s => s.trim()).filter(Boolean);
      parsedSegments.push({ name: segName, sub_segments: subs });
    }
  }

  // Key Players
  const players = [];
  const playerSection = fullText.match(/(?:Key Players|Top Companies|Competitive Landscape)[^:]*:\s*([^.\n]+)/i);
  if (playerSection && playerSection[1]) {
    const list = playerSection[1].split(/,|\n/).map(p => p.trim()).filter(Boolean);
    players.push(...list);
  }

  // Custom sections
  const customSections = [];
  const customMatch = fullText.match(/(?:Custom Requirements|Client Requirements)[^:]*:\s*([^.]+)/i);
  if (customMatch && customMatch[1]) {
    const reqs = customMatch[1].split(/;|\n|\d+\./).map(r => r.trim()).filter(r => r.length > 5);
    for (const r of reqs) {
      customSections.push({ title: r });
    }
  }

  return {
    market_name: marketName,
    market_name_upper: marketName.toUpperCase(),
    market_name_title: marketName,
    parsed_segments: parsedSegments,
    parsed_players: players,
    custom_sections: customSections,
    report_geography: "Global",
    company_name: "NextGen Intelligence Stats and Consulting LLP",
    base_year: "2024",
    forecast_start_year: "2025",
    forecast_end_year: "2035",
    history_start_year: "2020",
    cover_title_truncated: marketName.length > 20,
  };
}

function buildPayload(aiContent, marketInput) {
  const core = marketInput.market_name;
  const segments = marketInput.parsed_segments || [];

  const val = (key, fallback = "") => (aiContent && aiContent[key]) ? String(aiContent[key]) : fallback;

  const payload = {
    "{{market_name}}": marketInput.market_name,
    "{{market_name_upper}}": marketInput.market_name_upper,
    "{{MARKET_NAME_UPPER}}": marketInput.market_name_upper,
    "{{report_geography}}": marketInput.report_geography,
    "{{company_name}}": marketInput.company_name,
    "{{base_year}}": marketInput.base_year,
    "{{forecast_start_year}}": marketInput.forecast_start_year,
    "{{forecast_end_year}}": marketInput.forecast_end_year,
    "{{history_start_year}}": marketInput.history_start_year,
    "{{co1_name_upper}}": val("co1_name", "Featured Company").toUpperCase(),
    "{{co2_name}}": val("co2_name", "Competitor 2"),
    "{{co3_name}}": val("co3_name", "Competitor 3"),
    "{{co4_name}}": val("co4_name", "Competitor 4"),
    "{{co5_name}}": val("co5_name", "Competitor 5"),
    "{{co6_name}}": val("co6_name", "Competitor 6"),
    "{{co7_name}}": val("co7_name", "Competitor 7"),
    "{{co8_name}}": val("co8_name", "Competitor 8"),
    "{{co9_name}}": val("co9_name", "Competitor 9"),
    "{{co10_name}}": val("co10_name", "Competitor 10"),
    "{{CO1_NAME}}": val("co1_name", "Featured Company").toUpperCase(),
    "{{CO2_NAME}}": val("co2_name", "Competitor 2").toUpperCase(),
    "{{CO3_NAME}}": val("co3_name", "Competitor 3").toUpperCase(),
    "{{CO4_NAME}}": val("co4_name", "Competitor 4").toUpperCase(),
    "{{CO5_NAME}}": val("co5_name", "Competitor 5").toUpperCase(),
    "{{CO6_NAME}}": val("co6_name", "Competitor 6").toUpperCase(),
    "{{CO7_NAME}}": val("co7_name", "Competitor 7").toUpperCase(),
    "{{CO8_NAME}}": val("co8_name", "Competitor 8").toUpperCase(),
    "{{CO9_NAME}}": val("co9_name", "Competitor 9").toUpperCase(),
    "{{CO10_NAME}}": val("co10_name", "Competitor 10").toUpperCase(),
    "{{co1_seg1_name}}": val("co1_segment_1_name", `${core} Segment 1`),
    "{{co1_seg2_name}}": val("co1_segment_2_name", `${core} Segment 2`),
    "{{segment5_marketshare1}}": val("segment5_marketshare1", "Sub-Segment 1"),
    "{{segment5_marketshare2}}": val("segment5_marketshare2", "Sub-Segment 2"),
    "{{segment5_marketshare3}}": val("segment5_marketshare3", "Sub-Segment 3"),
    "{{segment5_marketshare4}}": val("segment5_marketshare4", "Sub-Segment 4"),
    "{{segment6_marketshare1}}": val("segment6_marketshare1", "Sub-Segment 1"),
    "{{segment6_marketshare2}}": val("segment6_marketshare2", "Sub-Segment 2"),
    "{{segment6_marketshare3}}": val("segment6_marketshare3", "Sub-Segment 3"),
    "{{segment6_marketshare4}}": val("segment6_marketshare4", "Sub-Segment 4"),
  };

  // Segments mapping
  const typeKeys = ["type_segment_1", "type_segment_2", "type_segment_3"];
  typeKeys.forEach((key, i) => {
    if (segments[0] && segments[0].sub_segments && segments[0].sub_segments[i]) {
      payload[`{{${key}}}`] = segments[0].sub_segments[i];
    } else {
      payload[`{{${key}}}`] = val(key, `${core} Type ${i + 1}`);
    }
  });

  const techKeys = ["tech_segment_1", "tech_segment_2", "tech_segment_3"];
  techKeys.forEach((key, i) => {
    if (segments[1] && segments[1].sub_segments && segments[1].sub_segments[i]) {
      payload[`{{${key}}}`] = segments[1].sub_segments[i];
    } else {
      payload[`{{${key}}}`] = val(key, `${core} Tech ${i + 1}`);
    }
  });

  const appKeys = ["app_segment_1", "app_segment_2", "app_segment_3", "app_segment_4"];
  appKeys.forEach((key, i) => {
    if (segments[2] && segments[2].sub_segments && segments[2].sub_segments[i]) {
      payload[`{{${key}}}`] = segments[2].sub_segments[i];
    } else {
      payload[`{{${key}}}`] = val(key, `${core} App ${i + 1}`);
    }
  });

  const HARDCODED = new Set(["Type", "Technology", "Application"]);
  const segMapping = [
    [3, "seg4_name", ["seg4_sub1", "seg4_sub2", "seg4_sub3"]],
    [4, "seg5_name", ["seg5_sub1", "seg5_sub2", "seg5_sub3"]],
    [5, "seg6_name", ["seg6_sub1", "seg6_sub2", "seg6_sub3"]],
  ];

  segMapping.forEach(([idx, nameKey, subKeys]) => {
    if (segments[idx] && !HARDCODED.has(segments[idx].name)) {
      payload[`{{${nameKey}}}`] = segments[idx].name;
    } else {
      payload[`{{${nameKey}}}`] = val(nameKey, `Segment ${idx + 1}`);
    }
    subKeys.forEach((subKey, i) => {
      if (segments[idx] && segments[idx].sub_segments && segments[idx].sub_segments[i]) {
        payload[`{{${subKey}}}`] = segments[idx].sub_segments[i];
      } else {
        payload[`{{${subKey}}}`] = val(subKey, `Sub-Segment ${i + 1}`);
      }
    });
  });

  for (let i = 1; i <= 4; i++) {
    const key = `{{ch4_custom_section_${i}_title}}`;
    if (marketInput.custom_sections && marketInput.custom_sections.length >= i) {
      payload[key] = marketInput.custom_sections[i - 1].title;
    } else {
      payload[key] = `Client Requirement ${i}`;
    }
  }

  payload["{{ch4_custom_subsection_4_1_title}}"] = val("ch4_custom_subsection_4_1_title", "Client Requirement 4.1");

  return payload;
}

async function renderReportDocx(templateBuffer, placeholderDict, adjustCoverTitle) {
  const zip = await JSZip.loadAsync(templateBuffer);
  
  // Iterate all text files in zip and perform placeholder replacement
  const files = Object.keys(zip.files);
  for (const filename of files) {
    if (filename.endsWith('.xml') || filename.endsWith('.rels')) {
      let content = await zip.file(filename).async("text");
      
      for (const [key, val] of Object.entries(placeholderDict)) {
        if (content.includes(key)) {
          // Escape XML special characters
          const escapedVal = String(val)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&apos;');
          content = content.split(key).join(escapedVal);
        }
      }

      if (adjustCoverTitle && filename === 'word/document.xml') {
        content = content.replace(/w:sz w:val="88"/g, 'w:sz w:val="58"');
      }

      zip.file(filename, content);
    }
  }

  return await zip.generateAsync({ type: "nodebuffer", compression: "DEFLATE" });
}

function getHeaders() {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Content-Type": "application/json",
  };
}

exports.handler = async (event, context) => {
  const httpMethod = event.httpMethod || "GET";

  if (httpMethod === "OPTIONS") {
    return { statusCode: 200, headers: getHeaders(), body: "" };
  }

  const rootDir = path.resolve(__dirname, '..', '..');

  if (httpMethod === "GET") {
    let samples = [];
    try {
      const files = fs.readdirSync(rootDir);
      samples = files.filter(f => f.endsWith('.docx') && !f.startsWith('~$') && !f.toLowerCase().includes('template'));
    } catch (e) {
      samples = ["Global_BESS_Market_Segmentation.docx", "Global_Screw_Market_Segmentation.docx", "Global_Soda_Market_Segmentation.docx", "Sample_Green Methanol Market.docx"];
    }

    return {
      statusCode: 200,
      headers: getHeaders(),
      body: JSON.stringify({
        status: "online",
        service: "MarketIQ Report Generator API",
        samples: samples
      })
    };
  }

  if (httpMethod !== "POST") {
    return { statusCode: 405, headers: getHeaders(), body: JSON.stringify({ error: "Method not allowed" }) };
  }

  try {
    let bodyData = {};
    if (event.body) {
      const raw = event.isBase64Encoded ? Buffer.from(event.body, 'base64').toString('utf8') : event.body;
      bodyData = JSON.parse(raw);
    }

    const { file_data, sample_name, use_api, api_key } = bodyData;

    let inputBuffer = null;
    if (file_data) {
      inputBuffer = Buffer.from(file_data, 'base64');
    } else if (sample_name) {
      const samplePath = path.join(rootDir, sample_name);
      if (fs.existsSync(samplePath)) {
        inputBuffer = fs.readFileSync(samplePath);
      } else {
        return { statusCode: 404, headers: getHeaders(), body: JSON.stringify({ error: `Sample file '${sample_name}' not found` }) };
      }
    } else {
      return { statusCode: 400, headers: getHeaders(), body: JSON.stringify({ error: "No file_data or sample_name provided" }) };
    }

    // Step 1: Parse input docx
    const marketInput = await parseDocxBuffer(inputBuffer);

    // Step 2: AI Generation or Fallback
    let aiContent = null;
    const keyToUse = api_key || process.env.OPENROUTER_API_KEY;

    if (useApi !== false && keyToUse) {
      try {
        const prompt = `Generate market report content for ${marketInput.market_name_title}.\nReturn ONLY valid JSON format.`;
        const res = await fetch("https://openrouter.ai/api/v1/chat/completions", {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${keyToUse}`,
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            model: process.env.MODEL || "nvidia/nemotron-3-nano-30b-a3b:free",
            messages: [{ role: "user", content: prompt }]
          })
        });
        if (res.ok) {
          const json = await res.json();
          const contentStr = json.choices[0].message.content;
          aiContent = JSON.parse(contentStr.replace(/```json|```/g, '').trim());
        }
      } catch (e) {
        console.log("AI API call failed, using fallback content:", e.message);
      }
    }

    if (!aiContent) {
      aiContent = getFallbackContent(marketInput.market_name);
    }

    // Step 3: Build payload
    const payload = buildPayload(aiContent, marketInput);

    // Step 4: Render Template DOCX
    let templatePath = path.join(rootDir, "full_market_report_template_updated.docx");
    if (!fs.existsSync(templatePath)) {
      templatePath = path.join(rootDir, "templates", "master_template_v1.docx");
    }

    const templateBuffer = fs.readFileSync(templatePath);
    const outputBuffer = await renderReportDocx(templateBuffer, payload, marketInput.cover_title_truncated);

    const docxB64 = outputBuffer.toString('base64');
    const safeName = sanitizeFilename(marketInput.market_name);
    const downloadFilename = `report_${safeName}_${Date.now()}.docx`;

    const auditData = {
      market_name: marketInput.market_name,
      market_name_upper: marketInput.market_name_upper,
      generated_at: new Date().toISOString(),
      api_model: process.env.MODEL || "nvidia/nemotron-3-nano-30b-a3b:free",
      ai_content: aiContent,
      payload: payload,
    };

    return {
      statusCode: 200,
      headers: getHeaders(),
      body: JSON.stringify({
        success: true,
        market_name: marketInput.market_name,
        filename: downloadFilename,
        docx_base64: docxB64,
        audit_json: auditData
      })
    };

  } catch (err) {
    return {
      statusCode: 500,
      headers: getHeaders(),
      body: JSON.stringify({ error: err.message, stack: err.stack })
    };
  }
};
