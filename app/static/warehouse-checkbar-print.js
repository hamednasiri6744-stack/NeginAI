document.querySelectorAll('[data-print-date]').forEach(node=>{
  const date=new Date(node.dataset.printDate);
  if(!Number.isNaN(date.getTime()))node.textContent=new Intl.DateTimeFormat('fa-IR',{dateStyle:'short',timeStyle:'short',timeZone:'Asia/Tehran'}).format(date);
});
document.querySelector('#printCheckbar').addEventListener('click',async()=>{
  await document.fonts.ready;
  window.print();
});
