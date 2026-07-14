const { app } = require('electron');

app.whenReady()
  .then(() => {
    app.exit(0);
  })
  .catch(() => {
    app.exit(1);
  });
