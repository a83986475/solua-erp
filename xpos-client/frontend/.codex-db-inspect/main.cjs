const { app, safeStorage } = require("electron");
const fs = require("fs");
const path = require("path");
const mysql = require("mysql2/promise");

const userData = "C:\\Users\\Yang\\AppData\\Roaming\\xpos-frontend";
const configPath = path.join(userData, "db-config.json");
const outputPath = process.env.XPOS_DB_INSPECT_OUTPUT;

function writeResult(result) {
  if (outputPath) fs.writeFileSync(outputPath, JSON.stringify(result, null, 2), "utf8");
}

app.setPath("userData", userData);
app.whenReady().then(async () => {
  let pool;
  try {
    const config = JSON.parse(fs.readFileSync(configPath, "utf8"));
    let password = config.password || "";
    if (password.startsWith("enc:v1:")) {
      password = safeStorage.decryptString(Buffer.from(password.slice("enc:v1:".length), "base64"));
    }
    pool = await mysql.createPool({
      host: config.host,
      port: config.port,
      user: config.user,
      password,
      database: config.database,
      connectionLimit: 1,
      charset: "utf8mb4",
      timezone: "+00:00",
    });

    const [profiles] = await pool.query(
      "SELECT name, company, warehouse, selling_price_list, disabled FROM pos_profiles ORDER BY name",
    );
    const [items] = await pool.query(
      "SELECT i.item_code, i.item_name, i.has_variants, i.variant_of, i.disabled, i.standard_rate, " +
        "COALESCE((SELECT ip.price_list_rate FROM item_prices ip WHERE ip.item_code=i.item_code " +
        "AND ip.selling=1 ORDER BY ip.valid_from DESC LIMIT 1), i.standard_rate, 0) AS effective_rate " +
        "FROM items i WHERE i.disabled=0 ORDER BY i.item_code",
    );
    const [bins] = await pool.query(
      "SELECT name, item_code, warehouse, actual_qty, projected_qty, reserved_qty, ordered_qty, modified, synced_at " +
        "FROM bins WHERE item_code IN ('SH151169-3MD-PT','SH151169-3MD-PT-01','SH151169-3MD-PT-02') " +
        "OR warehouse='Stores - SH' ORDER BY warehouse, item_code LIMIT 200",
    );
    const [stockCache] = await pool.query(
      "SELECT cache_key, item_code, warehouse, actual_qty, updated_at FROM stock_cache " +
        "WHERE warehouse='Stores - SH' OR item_code='SH151169-3MD-PT' ORDER BY warehouse, item_code LIMIT 200",
    );
    const [meta] = await pool.query(
      "SELECT `key`, updated_at, CHAR_LENGTH(`value`) AS value_length FROM sync_meta " +
        "WHERE `key` NOT IN ('api_key','api_secret','hub_api_secret') ORDER BY `key`",
    );
    const [pending] = await pool.query(
      "SELECT 'pending_invoices' AS table_name, status, COUNT(*) AS count FROM pending_invoices GROUP BY status " +
        "UNION ALL SELECT 'pending_purchases', status, COUNT(*) FROM pending_purchases GROUP BY status " +
        "UNION ALL SELECT 'deletion_log', 'rows', COUNT(*) FROM deletion_log",
    );
    const [counts] = await pool.query(
      "SELECT 'items' AS table_name, COUNT(*) AS count FROM items WHERE disabled=0 " +
        "UNION ALL SELECT 'bins', COUNT(*) FROM bins WHERE warehouse='Stores - SH' " +
        "UNION ALL SELECT 'stock_cache', COUNT(*) FROM stock_cache WHERE warehouse='Stores - SH'",
    );

    const tableNames = ["items", "item_prices", "bins", "stock_cache", "pos_profiles", "sync_meta", "pending_invoices", "pending_purchases", "deletion_log"];
    const structure = {};
    for (const table of tableNames) {
      const [rows] = await pool.query(`SHOW CREATE TABLE \`${table}\``);
      structure[table] = rows[0]?.["Create Table"] || null;
    }

    writeResult({
      config: { host: config.host, port: config.port, user: config.user, database: config.database },
      profiles,
      items,
      bins,
      stockCache,
      meta,
      pending,
      counts,
      structure,
    });
  } catch (error) {
    writeResult({ error: error instanceof Error ? error.message : String(error) });
    process.exitCode = 1;
  } finally {
    if (pool) await pool.end();
    app.quit();
  }
});
