import { MaterialSymbolsLightCollectionsBookmarkRounded } from "../icons";

interface NameTitleProps {
    title: string
}

const NameTitle: React.FC<NameTitleProps> = (props) => {
    return (
        <div className="w-full flex items-center text-xl text-black font-semibold my-4">
            <MaterialSymbolsLightCollectionsBookmarkRounded className="text-[#8093f3] mr-1 font-bold" />
            <span>{props.title}</span>
        </div>
    );
};

export default NameTitle;
