import { GisLayerStack } from "../icons";

interface VetCardProps {
    title: string;
    children?: React.ReactNode;
}

const VetCard: React.FC<VetCardProps> = (props) => {
    return (
        <section className="w-full px-5 py-3 bg-white rounded-lg mt-2">
            <h3 className="font-bold   flex items-center">
                <GisLayerStack className="text-[#8093f3] inline-block font-bold mr-2" />
                {props.title}
            </h3>
            <div>
                {props.children}
            </div>
        </section>
    )
};

export default VetCard;
