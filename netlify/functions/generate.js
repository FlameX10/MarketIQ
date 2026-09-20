const JSZip = require('jszip');
const fs = require('fs');
const path = require('path');

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
    type_segment_1: `${core} Standard Grade`,
    type_segment_2: `${core} Premium Grade`,
    type_segment_3: `${core} Specialized Grade`,
    tech_segment_1: "Advanced Automated Processing",
    tech_segment_2: "NextGen Manufacturing",
    tech_segment_3: "High-Efficiency Production",
    app_segment_1: "Industrial Applications",
    app_segment_2: "Commercial Sector",
    app_segment_3: "Residential Sector",
    app_segment_4: "Specialty Applications",
    co1_name: `Global ${core} Leaders`,
    co2_name: `${core} Innovations Inc`,
    co3_name: `Apex ${core} Solutions`,
    co4_name: `Prime ${core} Corp`,
    co5_name: `Vanguard ${core}`,
    co6_name: `United ${core}`,
    co7_name: `International ${core}`,
    co8_name: `Strategic ${core}`,
    co9_name: `Pioneer ${core}`,
    co10_name: `Global ${core} Enterprise`,
    co1_segment_1_name: `Core ${core} Products`,
    co1_segment_2_name: `${core} Services & Accessories`,
    segment5_marketshare1: "Direct Enterprise Sales",
    segment5_marketshare2: "Distributor Network",
    segment5_marketshare3: "Online Channels",
    segment6_marketshare1: "Premium Material",
    segment6_marketshare2: "Standard Material",
    segment6_marketshare3: "Composite Material",
    segment6_marketshare4: "Eco-friendly Material",
    seg4_name: "End User",
    seg4_sub1: "Industrial End Users",
    seg4_sub2: "Commercial End Users",
    seg4_sub3: "Individual Consumers",
    seg5_name: "Distribution Channel",
    seg5_sub1: "Direct Enterprise Sales",
    seg5_sub2: "Distributor Network",
    seg5_sub3: "Online E-Commerce",
    seg6_name: "Material",
    seg6_sub1: "Premium Material",
    seg6_sub2: "Standard Material",
    seg6_sub3: "Composite Material",
    ch4_custom_subsection_4_1_title: `Strategic Analysis of ${core} Market Opportunities`,
  };
}

function validatePayload(payloadDict) {
  const genericPatterns = [
    [/\b(Type|Tech|App)\s+\d+\b/i, "Generic segment placeholder (e.g. Type 1, Tech 2, App 3)"],
    [/\bSegment\s+[456]\b/i, "Generic dimension name (e.g. Segment 4, Segment 5, Segment 6)"],
    [/\bSub-Segment\s*\d*\b/i, "Generic sub-segment label"],
    [/\bClient Requirement\s*\d*(\.\d+)?\b/i, "Generic client requirement title"],
    [/\bFEATURED COMPANY\b/i, "Generic company placeholder"],
    [/\bCompetitor\s+\d+\b/i, "Generic competitor placeholder"],
    [/www\.FEATURED\s*COMPANY\.com/i, "Fake company URL"],
  ];

  const errors = [];
  for (const [key, val] of Object.entries(payloadDict)) {
    if (!val || typeof val !== 'string') continue;
    for (const [pattern, desc] of genericPatterns) {
      if (pattern.test(val)) {
        errors.append ? errors.append(`${key}: ${val}`) : errors.push(`Unresolved placeholder in '${key}': '${val}' (${desc})`);
      }
    }
  }

  return { isValid: errors.length === 0, errors };
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

  // Multi-pattern Segment Parser
  const parsedSegments = [];
  const segMap = {};

  // Pattern A: Inline lines like "1. Type: Porcelain, Glazed..." or "By Type: ..."
  const inlineLines = fullText.match(/(?:By\s+|\d+[\.\)]\s*)?([A-Za-z0-9\s/&\-]+?)\s*:\s*([^.\n]+)/g) || [];
  for (const line of inlineLines) {
    const parts = line.split(':');
    if (parts.length >= 2) {
      const header = parts[0].replace(/^(?:By\s+|\d+[\.\)]\s*)/i, '').trim();
      const vals = parts[1].split(/[,;\n]/).map(s => s.trim()).filter(Boolean);
      const hLower = header.toLowerCase();
      if (!hLower.includes('global') && !hLower.includes('market') && !hLower.includes('player') && !hLower.includes('custom') && vals.length > 0) {
        segMap[header] = vals;
      }
    }
  }

  // Convert segMap to parsedSegments array
  for (const [name, subs] of Object.entries(segMap)) {
    parsedSegments.push({ name, sub_segments: subs });
  }

  // Key Players
  const players = [];
  const playerSection = fullText.match(/(?:Key Players|Top Companies|Competitive Landscape)[^:]*:\s*([^.\n]+)/i);
  if (playerSection && playerSection[1]) {
    const list = playerSection[1].split(/,|\n/).map(p => p.trim().replace(/^[-•*\d+.]\s*/, '')).filter(Boolean);
    players.push(...list);
  }

  // Custom sections
  const customSections = [];
  const customMatch = fullText.match(/(?:Custom Requirements|Client Requirements)[^:]*:\s*([^.]+)/i);
  if (customMatch && customMatch[1]) {
    const reqs = customMatch[1].split(/;|\n|\d+\./).map(r => r.trim().replace(/^[-•*\d+.]\s*/, '')).filter(r => r.length > 5);
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
  const players = marketInput.parsed_players || [];
  const customReqs = marketInput.custom_sections || [];

  const val = (key, fallback = "") => (aiContent && aiContent[key]) ? String(aiContent[key]) : fallback;

  // 1. Key Players Mapping (Priority: Parsed players > AI content > Domain Fallback)
  const coNames = {};
  for (let i = 1; i <= 10; i++) {
    if (players.length >= i && players[i - 1]) {
      coNames[`co${i}_name`] = players[i - 1];
    } else {
      coNames[`co${i}_name`] = val(`co${i}_name`, `Global ${core} Leader ${i}`);
    }
  }

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
    "{{co1_name_upper}}": coNames["co1_name"].toUpperCase(),
    "{{co1_seg1_name}}": val("co1_segment_1_name", `${core} Primary Segment`),
    "{{co1_seg2_name}}": val("co1_segment_2_name", `${core} Secondary Segment`),
  };

  for (let i = 1; i <= 10; i++) {
    const cName = coNames[`co${i}_name`];
    payload[`{{co${i}_name}}`] = cName;
    payload[`{{CO${i}_NAME}}`] = cName.toUpperCase();
  }

  // 2. Semantic Segment Categorization
  let typeSeg = null, techSeg = null, appSeg = null;
  const unusedSegs = [];

  for (const seg of segments) {
    const nameLower = seg.name.toLowerCase();
    if (!typeSeg && (nameLower.includes('type') || nameLower.includes('product') || nameLower.includes('form') || nameLower.includes('grade'))) {
      typeSeg = seg;
    } else if (!techSeg && (nameLower.includes('tech') || nameLower.includes('process') || nameLower.includes('method'))) {
      techSeg = seg;
    } else if (!appSeg && (nameLower.includes('app') || nameLower.includes('end-use') || nameLower.includes('use'))) {
      appSeg = seg;
    } else {
      unusedSegs.push(seg);
    }
  }

  const remaining = segments.filter(s => s !== typeSeg && s !== techSeg && s !== appSeg);
  if (!typeSeg && remaining.length > 0) typeSeg = remaining.shift();
  if (!techSeg && remaining.length > 0) techSeg = remaining.shift();
  if (!appSeg && remaining.length > 0) appSeg = remaining.shift();

  // Map Type Sub-Segments
  ["type_segment_1", "type_segment_2", "type_segment_3"].forEach((key, i) => {
    if (typeSeg && typeSeg.sub_segments && typeSeg.sub_segments[i]) {
      payload[`{{${key}}}`] = typeSeg.sub_segments[i];
    } else {
      payload[`{{${key}}}`] = val(key, `${core} Variant ${i + 1}`);
    }
  });

  // Map Tech Sub-Segments
  ["tech_segment_1", "tech_segment_2", "tech_segment_3"].forEach((key, i) => {
    if (techSeg && techSeg.sub_segments && techSeg.sub_segments[i]) {
      payload[`{{${key}}}`] = techSeg.sub_segments[i];
    } else {
      payload[`{{${key}}}`] = val(key, `${core} Technology ${i + 1}`);
    }
  });

  // Map App Sub-Segments
  ["app_segment_1", "app_segment_2", "app_segment_3", "app_segment_4"].forEach((key, i) => {
    if (appSeg && appSeg.sub_segments && appSeg.sub_segments[i]) {
      payload[`{{${key}}}`] = appSeg.sub_segments[i];
    } else {
      payload[`{{${key}}}`] = val(key, `${core} Application ${i + 1}`);
    }
  });

  // Map Segments 4, 5, 6
  const segConfigs = [
    ["seg4_name", ["seg4_sub1", "seg4_sub2", "seg4_sub3"], null],
    ["seg5_name", ["seg5_sub1", "seg5_sub2", "seg5_sub3"], ["segment5_marketshare1", "segment5_marketshare2", "segment5_marketshare3", "segment5_marketshare4"]],
    ["seg6_name", ["seg6_sub1", "seg6_sub2", "seg6_sub3"], ["segment6_marketshare1", "segment6_marketshare2", "segment6_marketshare3", "segment6_marketshare4"]],
  ];

  const unassigned = segments.filter(s => s !== typeSeg && s !== techSeg && s !== appSeg);

  segConfigs.forEach(([nameKey, subKeys, shareKeys], idx) => {
    const currSeg = unassigned[idx] || null;
    const dimensionName = (currSeg && currSeg.name) ? currSeg.name : val(nameKey, `${core} Dimension ${idx + 4}`);
    payload[`{{${nameKey}}}`] = dimensionName;

    subKeys.forEach((subKey, i) => {
      if (currSeg && currSeg.sub_segments && currSeg.sub_segments[i]) {
        payload[`{{${subKey}}}`] = currSeg.sub_segments[i];
      } else {
        payload[`{{${subKey}}}`] = val(subKey, `${dimensionName} Sub-category ${i + 1}`);
      }
    });

    if (shareKeys) {
      shareKeys.forEach((shareKey, i) => {
        if (currSeg && currSeg.sub_segments && currSeg.sub_segments[i]) {
          payload[`{{${shareKey}}}`] = currSeg.sub_segments[i];
        } else {
          payload[`{{${shareKey}}}`] = val(shareKey, `${dimensionName} Option ${i + 1}`);
        }
      });
    }
  });

  // 3. Client Requirements Mapping
  for (let i = 1; i <= 4; i++) {
    const key = `{{ch4_custom_section_${i}_title}}`;
    if (customReqs.length >= i && customReqs[i - 1].title) {
      payload[key] = customReqs[i - 1].title;
    } else {
      payload[key] = val(`ch4_custom_section_${i}_title`, `${core} Custom Analysis ${i}`);
    }
  }

  if (customReqs.length >= 1 && customReqs[0].title) {
    payload["{{ch4_custom_subsection_4_1_title}}"] = customReqs[0].title;
  } else {
    payload["{{ch4_custom_subsection_4_1_title}}"] = val("ch4_custom_subsection_4_1_title", `${core} In-Depth Requirement Analysis`);
  }

  return payload;
}

async function renderReportDocx(templateBuffer, placeholderDict, adjustCoverTitle) {
  const zip = await JSZip.loadAsync(templateBuffer);
  
  const files = Object.keys(zip.files);
  for (const filename of files) {
    if (filename.endsWith('.xml') || filename.endsWith('.rels')) {
      let content = await zip.file(filename).async("text");
      
      for (const [key, val] of Object.entries(placeholderDict)) {
        if (content.includes(key)) {
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

    if (use_api !== false && keyToUse) {
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

    // Validate payload before rendering
    const validation = validatePayload(payload);
    if (!validation.isValid) {
      console.warn("Payload validation warnings/errors:", validation.errors);
    }

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

module.exports = {
  handler: exports.handler,
  parseDocxBuffer,
  buildPayload,
  getFallbackContent,
  validatePayload,
};
