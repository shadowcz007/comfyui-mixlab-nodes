import { app } from '../../../scripts/app.js'

async function getCustomnodeMappings (mode = 'url') {
  // mode = "local";
  let api_host = `${window.location.hostname}:${window.location.port}`
  let api_base = ''
  let url = `${window.location.protocol}//${api_host}${api_base}`

  let nodes = {}
  try {
    const response = await fetch(`${url}/customnode/getmappings?mode=${mode}`)
    const data = await response.json()
    for (let url in data) {
      let n = data[url]
      for (let node of n[0]) {
        if(node=='CLIPSeg')console.log('#CLIPSeg',n)
        nodes[node] = { url, title: n[1].title_aux }
      }
    }
  } catch (error) {}

  return nodes
}

const missingNodeGithub = (missingNodeTypes, nodesMap) => {
  let ts = {}

  Array.from(new Set(missingNodeTypes), n => {
    if (nodesMap[n]) {
      let title = nodesMap[n].title
      if (!ts[title]) {
        ts[title] = {
          title,
          nodes: {},
          url: nodesMap[n].url
        }
      }
      ts[title].nodes[n] = 1
    } else {
      ts[n] = {
        title: n,
        nodes: {},
        url: `https://github.com/search?q=${n}&type=code`
      }
      ts[n].nodes[n] = 1
    }
  })

  return Array.from(Object.values(ts), n => {
    const url = n.url
    return `<li style="color: white;
   background: black;
   padding: 8px;
   font-size: 12px;">${n.title}<a href="${url}" target="_blank"> 🔗</a></li>`
  })
}

app.showMissingNodesError = async function (
  missingNodeTypes,
  hasAddedNodes = true
) {

  const nodesMap = await getCustomnodeMappings()
  console.log('#nodesMap', nodesMap)
    console.log('###MIXLAB', missingNodeTypes, hasAddedNodes)
  this.ui.dialog.show(
    `When loading the graph, the following node types were not found: <ul>${missingNodeGithub(
      missingNodeTypes,
      nodesMap
    ).join('')}</ul>${
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
