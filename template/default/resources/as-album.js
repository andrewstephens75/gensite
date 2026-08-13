// bare-bones album component, designed to style properly with the rest of my template
// which is why it doesn't use a shadow dom
//
// usage:
//  <as-album>
//     <a href="fullsize1.jpg"><img src=thumb1.jpg alt="image description"/></a>
//     <a href="fullsize2.jpg"><img src=thumb2.jpg alt="image description"/></a>
//     <a href="fullsize3.jpg"><img src=thumb3.jpg alt="image description"/></a>
// </as-album>



const ALBUMTEMPLATE = `
<figure id="albumdisplay">
  <img id="display" src="" alt=""/>
  <figcaption id="caption"></figcaption>
</figure>
<div id="thumbscontainer">
</div>
`

const ALBUMSTYLES = `

#albumdisplay {
    width: 100%;
    max-width: 100%;
    margin: 0px;
}

#display {
    object-fit: contain;
    max-width: 100%;
}

#thumbscontainer {
  float: none;
  clear: both;
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: minmax(100px, 1fr);
  gap: 0.5rem;
  max-height: 140px; 
  height: 140px;
  max-width: 100%;
  overflow: auto; 
  min-height: 0; 
  min-width: 0;

}

#thumbscontainer img {
  width: 100%;
  height: 110px;
  object-fit: contain;
  box-sizing: border-box; 
}

#thumbscontainer img.selected {
  border: red solid 5px;
  background-color: pink;
}
`

class AsAlbum extends HTMLElement {
    constructor() {
        super();
    }

    connectedCallback() {

        setTimeout((() => {
            this.getListOfPictures()
            this.replaceContents()
            this.populateThumbs()
            this.setSelectThumbnailIndex(0)
        }).bind(this), 0)
        console.log("Custom element added to page.");
    }

    attributeChangedCallback(name, oldValue, newValue) {
        console.log(`Attribute ${name} has changed.`);
    }

    replaceContents() {
        this.replaceChildren()
        this.classList.add("customelement")

        let styleElement = document.createElement("style")
        styleElement.innerHTML = ALBUMSTYLES
        this.innerHTML = ALBUMTEMPLATE
        document.body.appendChild(styleElement)
    }

    getListOfPictures() {
        this._pictures = []
        // grab the list of child elements and construct the list of images
        let links = this.getElementsByTagName("a")
        for (const link of links) {
            const fullsize_url = link.getAttribute("href")
            const img = link.children[0]
            const caption = img.getAttribute("alt")
            const thumb_url = img.getAttribute("src")

            let picture = { "index": this._pictures.length, "fullsize_url": fullsize_url, "caption": caption, "thumb_url": thumb_url }
            this._pictures.push(picture)
            console.log(picture)
        }
    }

    populateThumbs() {
        let container = this.querySelector("#thumbscontainer")
        for (const i of this._pictures) {
            let image_element = document.createElement("img")
            image_element.src = i.thumb_url
            image_element.addEventListener("click", (() => {
                this.setSelectThumbnailIndex(i.index);
            }).bind(this))
            container.appendChild(image_element)
        }
    }

    setSelectThumbnailIndex(index) {
        let thumbContainer = this.querySelector("#thumbscontainer")

        let thumbElements = this.querySelectorAll("#thumbscontainer>img")
        for (let i = 0; i < thumbElements.length; ++i) {
            let e = thumbElements[i]
            if (i == index) {
                e.classList.add('selected')
                e.scrollIntoView({ behavior: "smooth", block: "center", inline: "center" })
                let mainImageElement = this.querySelector("#display")
                let captionElement = this.querySelector("#caption")

                mainImageElement.src = this._pictures[index].fullsize_url
                mainImageElement.setAttribute("alt", this._pictures[index].caption)
                captionElement.innerHTML = this._pictures[index].caption
            } else {
                e.classList.remove('selected')
            }
        }
    }
}

customElements.define("as-album", AsAlbum);