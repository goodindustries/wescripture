const { handler } = require("./monitor_sample.js");

exports.config = {
  schedule: "@daily",
};

exports.handler = async function () {
  return handler();
};

