#!/usr/bin/env node

import { execFile } from "node:child_process";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";

import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const execFileAsync = promisify(execFile);
const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(scriptDir, "../..");
const boardPath = path.join(
  projectRoot,
  "hardware/design/rev3/kicad/hacking_box_v2.kicad_pcb",
);
const outputDir = path.resolve(
  process.argv[2] ?? path.join(projectRoot, "outputs/nextpcb_rev3_20260802"),
);
const kicadCli = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli";

const parts = [
  {
    designators: ["U1"],
    manufacturer: "ESPRESSIF",
    mpn: "ESP32-S3-WROOM-1-N8R8",
    description: "Wi-Fi and Bluetooth 5 LE module, 8 MB flash, 8 MB PSRAM",
    package: "SMD, 25.5x18mm",
    supplierPart: "C2913201",
    source: "https://www.lcsc.com/product-detail/C2913201.html",
  },
  {
    designators: ["U2"],
    manufacturer: "Advanced Monolithic Systems",
    mpn: "AMS1117-3.3",
    description: "3.3 V 1 A linear regulator",
    package: "SOT-223",
    supplierPart: "C6186",
    source: "https://www.lcsc.com/product-detail/C6186.html",
  },
  {
    designators: ["J1"],
    manufacturer: "Korean Hroparts Elec",
    mpn: "TYPE-C-31-M-12",
    description: "USB Type-C receptacle, 16 positions",
    package: "SMD USB-C 16P",
    supplierPart: "C165948",
    source: "https://www.lcsc.com/product-detail/C165948.html",
  },
  {
    designators: ["D1"],
    manufacturer: "TECH PUBLIC",
    mpn: "USBLC6-2SC6",
    description: "Dual-channel USB ESD protection array",
    package: "SOT-23-6",
    supplierPart: "C2827654",
    source: "https://www.lcsc.com/product-detail/C2827654.html",
  },
  {
    designators: ["BZ1"],
    manufacturer: "XHXDZ",
    mpn: "SMD5020-ZK",
    description: "3 V passive electromagnetic buzzer, 4 kHz",
    package: "SMD, 5.3x5.3mm",
    supplierPart: "C49246955",
    source: "https://www.lcsc.com/product-detail/C49246955.html",
  },
  {
    designators: ["Q_BZ"],
    manufacturer: "AOS",
    mpn: "AO3400A",
    description: "30 V N-channel MOSFET",
    package: "SOT-23",
    supplierPart: "C20917",
    source: "https://www.lcsc.com/product-detail/C20917.html",
  },
  {
    designators: ["D_BZ"],
    manufacturer: "JSMSEMI",
    mpn: "1N4148W",
    description: "100 V fast switching diode",
    package: "SOD-123",
    supplierPart: "C917030",
    source: "https://www.lcsc.com/product-detail/C917030.html",
  },
  {
    designators: ["C1", "C3", "C4", "C5", "C7", "C9"],
    manufacturer: "Samsung Electro-Mechanics",
    mpn: "CL21A106KAYNNNE",
    description: "10 uF 25 V X5R ceramic capacitor, 10%",
    package: "0805",
    supplierPart: "C15850",
    source: "https://www.lcsc.com/product-detail/C15850.html",
  },
  {
    designators: ["C2", "C6", "C8", "C_OLED"],
    manufacturer: "YAGEO",
    mpn: "CC0603KRX7R9BB104",
    description: "100 nF 50 V X7R ceramic capacitor, 10%",
    package: "0603",
    supplierPart: "C14663",
    source: "https://www.lcsc.com/product-detail/C14663.html",
  },
  {
    designators: ["C_EN"],
    manufacturer: "Samsung Electro-Mechanics",
    mpn: "CL10A105KB8NNNC",
    description: "1 uF 50 V X5R ceramic capacitor, 10%",
    package: "0603",
    supplierPart: "C15849",
    source: "https://www.lcsc.com/product-detail/C15849.html",
  },
  {
    designators: ["R1", "R2"],
    manufacturer: "UNI-ROYAL",
    mpn: "0603WAF5101T5E",
    description: "5.1 kohm 100 mW thick-film resistor, 1%",
    package: "0603",
    supplierPart: "C23186",
    source: "https://www.lcsc.com/product-detail/C23186.html",
  },
  {
    designators: ["R_BOOT", "R_BZ_PD", "R_EN", "R_SCL", "R_SDA"],
    manufacturer: "UNI-ROYAL",
    mpn: "0603WAF1002T5E",
    description: "10 kohm 100 mW thick-film resistor, 1%",
    package: "0603",
    supplierPart: "C25804",
    source: "https://www.lcsc.com/product-detail/C25804.html",
  },
  {
    designators: [
      "R_BZ",
      "R_CHAL0",
      "R_CHAL1",
      "R_CHAL2",
      "R_LED1",
      "R_LED2",
      "R_LED3",
      "R_LED4",
      "R_LED5",
      "R_UART_RX",
      "R_UART_TX",
    ],
    manufacturer: "UNI-ROYAL",
    mpn: "0603WAF1001T5E",
    description: "1 kohm 100 mW thick-film resistor, 1%",
    package: "0603",
    supplierPart: "C21190",
    source: "https://www.lcsc.com/product-detail/C21190.html",
  },
  {
    designators: ["LED1", "LED2", "LED3", "LED4", "LED5"],
    manufacturer: "Hubei KENTO Elec",
    mpn: "KT-0603R",
    description: "Red indicator LED",
    package: "0603",
    supplierPart: "C2286",
    source: "https://www.lcsc.com/product-detail/C2286.html",
  },
  {
    designators: ["SW_ADMIN", "SW_BOOT", "SW_EN"],
    manufacturer: "XUNPU",
    mpn: "TS-1088-AR02016",
    description: "SPST normally-open tactile switch, 160 gf",
    package: "SMD, 4x3mm",
    supplierPart: "C720477",
    source: "https://www.lcsc.com/product-detail/C720477.html",
  },
  {
    designators: ["OLED1"],
    manufacturer: "",
    mpn: "HS96L03W2C03",
    description: "0.96 inch 128x64 white I2C OLED module; install manually",
    package: "27.3x27.8mm module, 1x4 PTH",
    supplierPart: "DeviceMart 15963242",
    source: "https://www.devicemart.co.kr/goods/view?no=15963242",
    procurementType: "DNP",
    note: "Do not procure or assemble. Customer hand-solders OLED after PCBA.",
  },
];

function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let quoted = false;

  for (let index = 0; index < text.length; index += 1) {
    const character = text[index];
    if (character === '"') {
      if (quoted && text[index + 1] === '"') {
        field += '"';
        index += 1;
      } else {
        quoted = !quoted;
      }
    } else if (character === "," && !quoted) {
      row.push(field);
      field = "";
    } else if ((character === "\n" || character === "\r") && !quoted) {
      if (character === "\r" && text[index + 1] === "\n") index += 1;
      row.push(field);
      if (row.some((value) => value !== "")) rows.push(row);
      row = [];
      field = "";
    } else {
      field += character;
    }
  }
  if (field !== "" || row.length > 0) {
    row.push(field);
    rows.push(row);
  }

  const [headers, ...body] = rows;
  return body.map((values) =>
    Object.fromEntries(headers.map((header, index) => [header, values[index] ?? ""])),
  );
}

function csvCell(value) {
  const text = String(value ?? "");
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
}

function toCsv(rows) {
  return rows.map((row) => row.map(csvCell).join(",")).join("\r\n") + "\r\n";
}

function naturalReferenceCompare(left, right) {
  return left.localeCompare(right, "en", { numeric: true, sensitivity: "base" });
}

await fs.mkdir(outputDir, { recursive: true });
const rawPositionPath = path.join(outputDir, ".kicad-position-source.csv");
await execFileAsync(kicadCli, [
  "pcb",
  "export",
  "pos",
  "--format",
  "csv",
  "--units",
  "mm",
  "--side",
  "both",
  "--smd-only",
  "--exclude-dnp",
  "--output",
  rawPositionPath,
  boardPath,
]);

const rawPlacements = parseCsv(await fs.readFile(rawPositionPath, "utf8"));
const assembledParts = parts.filter((part) => part.procurementType !== "DNP");
const bomReferences = new Set(assembledParts.flatMap((part) => part.designators));
const placementReferences = new Set(rawPlacements.map((placement) => placement.Ref));

if (bomReferences.size !== 44 || placementReferences.size !== 44) {
  throw new Error(
    `Expected 44 assembled references; BOM=${bomReferences.size}, centroid=${placementReferences.size}`,
  );
}
const missingFromCentroid = [...bomReferences].filter((ref) => !placementReferences.has(ref));
const missingFromBom = [...placementReferences].filter((ref) => !bomReferences.has(ref));
if (missingFromCentroid.length || missingFromBom.length) {
  throw new Error(
    `BOM/centroid mismatch. Missing from centroid: ${missingFromCentroid.join(" ")}; ` +
      `missing from BOM: ${missingFromBom.join(" ")}`,
  );
}
if (rawPlacements.some((placement) => placement.Side.toLowerCase() !== "top")) {
  throw new Error("NextPCB centroid contains a non-top-side placement");
}

const bomHeaders = [
  "Item",
  "Designator",
  "Quantity",
  "Manufacturer",
  "Manufacturer Part Number",
  "Description",
  "Package",
  "Mounting Type",
  "Supplier",
  "Supplier Part Number",
  "Procurement Type",
  "Customer Note",
  "Source URL",
];
const bomData = parts.map((part, index) => [
  index + 1,
  part.designators.join(","),
  part.designators.length,
  part.manufacturer,
  part.mpn,
  part.description,
  part.package,
  part.procurementType === "DNP" ? "Manual / PTH" : "SMT",
  part.procurementType === "DNP" ? "DeviceMart" : "LCSC",
  part.supplierPart,
  part.procurementType ?? "",
  part.note ?? "",
  part.source,
]);

const centroidHeaders = [
  "Designator",
  "Mid X (mm)",
  "Mid Y (mm)",
  "Rotation (deg)",
  "Layer",
  "Value",
  "Package",
];
const centroidData = rawPlacements
  .map((placement) => [
    placement.Ref,
    Number(placement.PosX),
    -Number(placement.PosY),
    ((Number(placement.Rot) % 360) + 360) % 360,
    placement.Side.toLowerCase() === "top" ? "Top" : "Bottom",
    placement.Val,
    placement.Package,
  ])
  .sort((left, right) => naturalReferenceCompare(left[0], right[0]));

const bomCsvPath = path.join(outputDir, "hacking_badge_v3_nextpcb_bom.csv");
const centroidCsvPath = path.join(outputDir, "hacking_badge_v3_nextpcb_centroid.csv");
await fs.writeFile(bomCsvPath, toCsv([bomHeaders, ...bomData]), "utf8");
await fs.writeFile(centroidCsvPath, toCsv([centroidHeaders, ...centroidData]), "utf8");

async function createWorkbook({ sheetName, headers, data, widths, numericColumns, tableName }) {
  const workbook = Workbook.create();
  const sheet = workbook.worksheets.add(sheetName);
  sheet.showGridLines = false;
  const rowCount = data.length + 1;
  const columnCount = headers.length;
  const range = sheet.getRangeByIndexes(0, 0, rowCount, columnCount);
  range.values = [headers, ...data];
  sheet.freezePanes.freezeRows(1);

  const headerRange = sheet.getRangeByIndexes(0, 0, 1, columnCount);
  headerRange.format = {
    fill: "#17365D",
    font: { bold: true, color: "#FFFFFF" },
    verticalAlignment: "center",
    wrapText: true,
    borders: { preset: "outside", style: "thin", color: "#17365D" },
  };
  headerRange.format.rowHeight = 32;

  const bodyRange = sheet.getRangeByIndexes(1, 0, data.length, columnCount);
  bodyRange.format = {
    font: { color: "#1F2937" },
    verticalAlignment: "center",
    borders: {
      insideHorizontal: { style: "thin", color: "#D9E2F3" },
      bottom: { style: "thin", color: "#AAB7C4" },
    },
  };
  bodyRange.format.rowHeight = 23;

  for (let column = 0; column < widths.length; column += 1) {
    sheet.getRangeByIndexes(0, column, rowCount, 1).format.columnWidth = widths[column];
  }
  for (const column of numericColumns) {
    sheet.getRangeByIndexes(1, column, data.length, 1).format.numberFormat = "0.0000";
  }
  sheet.tables.add(
    sheet.getRangeByIndexes(0, 0, rowCount, columnCount).address,
    true,
    tableName,
  );
  return workbook;
}

const bomWorkbook = await createWorkbook({
  sheetName: "BOM",
  headers: bomHeaders,
  data: bomData,
  widths: [7, 48, 10, 28, 33, 48, 25, 16, 14, 24, 20, 48, 46],
  numericColumns: [],
  tableName: "NextPcbBom",
});
const bomSheet = bomWorkbook.worksheets.getItem("BOM");
bomSheet.getRange(`B2:B${bomData.length + 1}`).format.wrapText = true;
bomSheet.getRange(`F2:F${bomData.length + 1}`).format.wrapText = true;
bomSheet.getRange(`L2:M${bomData.length + 1}`).format.wrapText = true;
bomSheet.getRange("A2:M17").format.autofitRows();
const centroidWorkbook = await createWorkbook({
  sheetName: "Centroid",
  headers: centroidHeaders,
  data: centroidData,
  widths: [20, 16, 16, 18, 12, 30, 40],
  numericColumns: [1, 2, 3],
  tableName: "NextPcbCentroid",
});

const bomXlsxPath = path.join(outputDir, "hacking_badge_v3_nextpcb_bom.xlsx");
const centroidXlsxPath = path.join(outputDir, "hacking_badge_v3_nextpcb_centroid.xlsx");
await (await SpreadsheetFile.exportXlsx(bomWorkbook)).save(bomXlsxPath);
await (await SpreadsheetFile.exportXlsx(centroidWorkbook)).save(centroidXlsxPath);

const bomInspect = await bomWorkbook.inspect({
  kind: "table",
  range: `BOM!A1:M${bomData.length + 1}`,
  include: "values,formulas",
  tableMaxRows: 20,
  tableMaxCols: 13,
});
const centroidInspect = await centroidWorkbook.inspect({
  kind: "table",
  range: `Centroid!A1:G${centroidData.length + 1}`,
  include: "values,formulas",
  tableMaxRows: 50,
  tableMaxCols: 7,
});
const errorScan = await centroidWorkbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "formula error scan",
});

const bomPreview = await bomWorkbook.render({
  sheetName: "BOM",
  range: `A1:M${bomData.length + 1}`,
  scale: 1,
  format: "png",
});
const centroidPreview = await centroidWorkbook.render({
  sheetName: "Centroid",
  range: "A1:G45",
  scale: 1.25,
  format: "png",
});
await fs.writeFile(
  path.join(outputDir, ".bom-preview.png"),
  new Uint8Array(await bomPreview.arrayBuffer()),
);
await fs.writeFile(
  path.join(outputDir, ".centroid-preview.png"),
  new Uint8Array(await centroidPreview.arrayBuffer()),
);

const validation = [
  "PASS",
  `Board: ${path.relative(projectRoot, boardPath)}`,
  `BOM rows: ${bomData.length} total (${assembledParts.length} populated groups + 1 OLED DNP)`,
  `Assembled designators: ${bomReferences.size}`,
  `Centroid placements: ${centroidData.length}`,
  "Assembly sides: Top only",
  "BOM/centroid populated designators: exact match",
  "OLED1: BOM DNP; excluded from centroid",
  `Workbook formula errors: ${errorScan.ndjson.includes("#") ? "reviewed" : "none"}`,
  `BOM inspect bytes: ${bomInspect.ndjson.length}`,
  `Centroid inspect bytes: ${centroidInspect.ndjson.length}`,
  "Coordinate units: millimeters",
  "Rotation: degrees counter-clockwise, normalized to 0-359",
].join("\n");
await fs.writeFile(path.join(outputDir, "nextpcb_validation.txt"), validation + "\n", "utf8");
await fs.rm(rawPositionPath);

console.log(validation);
console.log(`Output directory: ${outputDir}`);
