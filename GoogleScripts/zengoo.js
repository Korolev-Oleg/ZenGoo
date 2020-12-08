function getSheetHeaders(sheet, filter) {
  let headers = sheet
    .getRange("1:1")
    .getValues()[0]

  if (filter) {
    headers = headers.filter(item => !!item)
  }
  return headers
}

function checkHeaders(sheet) {
  headers = [
    'date', 'categoryName', 'payee', 'comment',
    'outcomeAccountName', 'outcome', 'income',
    'outcomeCurrencyShortTitle', 'createdDate',
    'incomeAccountName', 'changedDate',
    'incomeCurrencyShortTitle', 'id']

  headers.sort()
  sheet.headers = getSheetHeaders(sheet, true)
  sheet.headers.sort()
  return String(sheet.headers) === String(headers)
}

function getColumnIndex(sheet, fieldTitle) {
  sheet.headers = getSheetHeaders(sheet, false)
  return sheet.headers.indexOf(fieldTitle) + 1
}

function currentDateTime() {
  let date = new Date()
  let time = `${date.getHours()}.${date.getMinutes()}.${date.getSeconds()}`
  return `${date.getFullYear()}.${date.getMonth()}.${date.getDay()} ${time}`
}

function setChangedDate(e) {
  let row = e.range.getRow()
  let sheet = e.source.getActiveSheet()
  let col = getColumnIndex(sheet, 'changedDate')
  let date = new Date()
  let idValue = sheet.getRange(row, getColumnIndex(sheet, 'id')).getValue()

  if (checkHeaders(sheet)) {
    if (idValue) {
      sheet.getRange(row, col)
        .setValue(
          date.toLocaleString()
        )
    }
  }
}

//function changeSubcategory(e) {
//  let sheet = e.source.getActiveSheet()
//  let ui = new SpreadsheetApp.getUi()
//  let catCol = getColumnIndex(sheet, 'categoryName')
//  //  let subCatCol = getColumnIndex(sheet, '')
//
//  if (checkHeaders(sheet)) {
//    if (sheet.getActiveCell().getColumn() === catCol && sheet.getActiveCell().getRow() > 1) {
//      //  sheet.getRange("R10:R17").setValue('XXX')
//    }
//  }
//}

function onEdit(e) {
  setChangedDate(e)
  //  changeSubcategory(e)
}

