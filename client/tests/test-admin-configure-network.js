describe("admin configure https", function() {
  var files = {
    priv_key: browser.gl.utils.makeTestFilePath("../../../backend/globaleaks/tests/data/https/valid/priv_key.pem"),
    cert: browser.gl.utils.makeTestFilePath("../../../backend/globaleaks/tests/data/https/valid/cert.pem"),
    chain: browser.gl.utils.makeTestFilePath("../../../backend/globaleaks/tests/data/https/valid/chain.pem"),
  };

  it("should interact with all ui elements", function() {
    var pk_panel = element(by.css("div.card.priv-key"));
    var csr_panel = element(by.css("div.card.csr"));
    var cert_panel = element(by.css("div.card.cert"));
    var chain_panel = element(by.css("div.card.chain"));
    var modal_action = by.id("modal-action-ok");

    browser.setLocation("admin/network");

    element(by.cssContainingText("a", "HTTPS")).click();

    element(by.model("admin.node.hostname")).clear();
    element(by.model("admin.node.hostname")).sendKeys("antani.gov");
    element(by.model("admin.node.hostname")).click();

    element.all(by.cssContainingText("button", "Save")).get(0).click();

    element(by.cssContainingText("button", "Proceed")).click();

    element(by.id("HTTPSManualMode")).click();

    // Generate key
    pk_panel.element(by.cssContainingText("button", "Generate")).click();

    // Generate csr
    element(by.id("csrGen")).click();

    csr_panel.element(by.model("csr_cfg.country")).sendKeys("IT");
    csr_panel.element(by.model("csr_cfg.province")).sendKeys("Liguria");
    csr_panel.element(by.model("csr_cfg.city")).sendKeys("Genova");
    csr_panel.element(by.model("csr_cfg.company")).sendKeys("Internet Widgets LTD");
    csr_panel.element(by.model("csr_cfg.department")).sendKeys("Suite reviews");
    csr_panel.element(by.model("csr_cfg.email")).sendKeys("nocontact@certs.may.hurt");
    element(by.id("csrSubmit")).click();

    // Download csr
    if (browser.gl.utils.testFileDownload()) {
      csr_panel.element(by.id("downloadCsr")).click();
    }

    // Delete csr
    element(by.id("deleteCsr")).click();
    browser.gl.utils.waitUntilPresent(modal_action);
    element(modal_action).click();
    browser.wait(protractor.ExpectedConditions.stalenessOf(element(by.id("deleteCsr"))));

    // Delete key
    element(by.id("deleteKey")).click();
    browser.gl.utils.waitUntilPresent(modal_action);
    element(modal_action).click();
    browser.wait(protractor.ExpectedConditions.stalenessOf(element(by.id("deleteKey"))));

    element(by.cssContainingText("button", "Proceed")).click();

    element(by.id("HTTPSManualMode")).click();

    if (browser.gl.utils.testFileUpload()) {
      browser.gl.utils.fixUploadButtons();

      // Upload key
      element(by.css("div.card.priv-key input[type=\"file\"]")).sendKeys(files.priv_key);

      // Upload cert
      element(by.css("div.card.cert input[type=\"file\"]")).sendKeys(files.cert);

      // Upload chain
      element(by.css("div.card.chain input[type=\"file\"]")).sendKeys(files.chain);

      // Download the cert and chain
      if (browser.gl.utils.testFileDownload()) {
        cert_panel.element(by.id("downloadCert")).click();
        chain_panel.element(by.id("downloadChain")).click();
      }

      // Delete chain, cert, key
      chain_panel.element(by.id("deleteChain")).click();
      browser.gl.utils.waitUntilPresent(modal_action);
      element(modal_action).click();

      cert_panel.element(by.id("deleteCert")).click();
      browser.gl.utils.waitUntilPresent(modal_action);
      element(modal_action).click();

      pk_panel.element(by.id("deleteKey")).click();
      browser.gl.utils.waitUntilPresent(modal_action);
      element(modal_action).click();
    }
  });
});
