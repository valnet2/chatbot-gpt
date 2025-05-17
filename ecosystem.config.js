module.exports = {
  apps : [{
    name   : "whatsapp-node",
    script : "./index.js",
    watch  : false
  },{
    name   : "whatsapp-flask",
    script : "./venv/bin/gunicorn",
    args   : "--workers 2 --bind 0.0.0.0:5000 --timeout 60 app:app", // Timeout aumentado a 60s
    interpreter: "./venv/bin/python",
    watch  : false
  }]
}
