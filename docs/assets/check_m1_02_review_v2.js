// Run with playwright-cli run-code --filename after loading the packet.
// This is UI QA in an isolated browser, never a human legal-review record.
async (page) => {
  const requests = [];
  page.on('request', request => {
    if (/^https?:/.test(request.url())) requests.push(request.url());
  });
  await page.context().setOffline(true);
  await page.getByText('Все 30 встроенных документов — справочно', {exact: true}).click();
  const buttons = page.locator('.source-list [data-document]');
  const count = await buttons.count();
  if (count !== 30) throw Error('Expected 30 documents, found '+count);
  let htmlDocuments = 0, pdfDocuments = 0, testedImages = 0;
  for (let i=0; i<count; i++) {
    const id = await buttons.nth(i).getAttribute('data-document');
    await buttons.nth(i).click();
    await page.locator('#viewer').waitFor({state:'visible'});
    if (await page.locator('#pdf-controls').isVisible()) {
      pdfDocuments++;
      await page.waitForFunction(() => {
        const img=document.querySelector('.page-image');
        return img && img.complete && img.naturalWidth>0;
      });
      testedImages++;
      const countText=await page.locator('#page-count').innerText();
      const last=Number(countText.split('/')[1]);
      // Click through the native controls, including the last page of long PDFs.
      for (let n=1;n<last;n++) await page.getByRole('button',{name:'Следующая страница',exact:true}).click();
      await page.waitForFunction(() => {
        const img=document.querySelector('.page-image');
        return img && img.complete && img.naturalWidth>0;
      });
      testedImages++;
      if (await page.locator('#page-count').innerText() !== last+' / '+last) throw Error('Wrong last page: '+id);
    } else {
      htmlDocuments++;
      if (!(await page.locator('#viewer-content article p').count())) throw Error('HTML did not render: '+id);
      if ((await page.locator('#viewer-content').innerText()).includes('\u003cp')) throw Error('Escaped markup displayed as text: '+id);
    }
    await page.getByRole('button',{name:'Закрыть документ',exact:true}).click();
    await page.locator('#viewer').waitFor({state:'hidden'});
  }
  if (requests.length) throw Error('Opening a document used the network: '+requests.join(', '));
  await page.getByRole('button',{name:'Сформировать ответ для чата',exact:true}).click();
  if (!(await page.locator('#status').innerText()).includes('Выберите решение')) throw Error('Blank decision accepted');
  await page.locator('#decision').selectOption('correction');
  await page.getByRole('button',{name:'Сформировать ответ для чата',exact:true}).click();
  if (!(await page.locator('#status').innerText()).includes('Укажите поправку')) throw Error('Empty correction accepted');
  await page.locator('#decision').selectOption('confirmed');
  await page.getByRole('button',{name:'Сформировать ответ для чата',exact:true}).click();
  const report=await page.locator('#report').inputValue();
  const json=JSON.parse(report.split('JSON для точной записи:\n')[1]);
  if (json.edition_admission!==false || json.question!=='59-ks19p-after-80' || json.engineering_open_items.length!==4 || !json.rationale) throw Error('Report changed review scope');
  await page.locator('#decision').selectOption('');
  await page.locator('#comment').fill('');
  await page.locator('#report').evaluate(el=>{el.value=''});
  return {documents:count, htmlDocuments, pdfDocuments, testedImages, documentNetworkRequests:requests.length, requiredDecisions:await page.locator('select#decision').count(), blankDecisionBlocked:true, emptyCorrectionBlocked:true, confirmationDoesNotRequireRewrittenRationale:true, editionAdmission:false, deliveredDecisionBlank:await page.locator('#decision').inputValue()===''};
}
