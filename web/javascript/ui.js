import { app } from '../../../scripts/app.js'

const missingNodeGithub = missingNodeTypes => {
  return Array.from(
    new Set(missingNodeTypes)
  ,n=>{
    const url = `https://github.com/search?q=${n}&type=code`;

   return `<li style="color: white;
   background: black;
   padding: 8px;
   font-size: 12px;">${n}<a href="${url}" target="_blank"> 🔗</a></li>`;
  })
}

app.showMissingNodesError = function (missingNodeTypes, hasAddedNodes = true) {
//   console.log('###MIXLAB', missingNodeTypes, hasAddedNodes)
  this.ui.dialog.show(
    `When loading the graph, the following node types were not found: <ul>${ missingNodeGithub(missingNodeTypes)
      .join('')}</ul>${
      hasAddedNodes
        ? 'Nodes that have failed to load will show as red on the graph.'
        : ''
    }`
  )
  this.logging.addEntry('Comfy.App', 'warn', {
    MissingNodes: missingNodeTypes
  })
}

// app.ui.dialog.show = function (html) {
//   console.log('###MIXLAB', html)
//   if (typeof html === 'string') {
//     this.textElement.innerHTML = html
//   } else {
//     this.textElement.replaceChildren(html)
//   }
//   this.element.style.display = 'flex'
// }
